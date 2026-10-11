import json
import os
import time
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential


load_dotenv()


# Stage 0+2: Define schema for parsed task
class ParsedTask(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    done: bool = Field(default=False)
    tags: Optional[list[str]] = Field(default=None)
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")


# Config
PROVIDER = os.getenv("LLM_PROVIDER", "stub").lower()
MODEL = os.getenv("LLM_MODEL", "google/gemma-3-12b-it:free")
BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
API_KEY = os.getenv("LLM_API_KEY", "")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "10"))
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("LLM_RETRY_BASE_DELAY", "0.5"))
KILL_SWITCH = os.getenv("LLM_KILL_SWITCH", "false").lower() == "true"
COST_PER_1K_IN = float(os.getenv("LLM_COST_PER_1K_TOKENS_IN", "0.0"))
COST_PER_1K_OUT = float(os.getenv("LLM_COST_PER_1K_TOKENS_OUT", "0.0"))


# In-memory cost log (simple)
_cost_log: list[Dict[str, Any]] = []


def get_cost_log() -> list[Dict[str, Any]]:
    return list(_cost_log)


def clear_cost_log() -> None:
    _cost_log.clear()


def log_cost(model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, latency_ms: int, success: bool, error: Optional[str] = None):
    cost_in = (prompt_tokens / 1000.0) * COST_PER_1K_IN
    cost_out = (completion_tokens / 1000.0) * COST_PER_1K_OUT
    total_cost = cost_in + cost_out
    entry = {
        "timestamp": time.time(),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "cost_usd": round(total_cost, 6),
        "success": success,
        "error": error,
    }
    _cost_log.append(entry)
    return entry


SYSTEM_PROMPT = """You are a strict JSON extractor. 
Your job is to parse messy task text into clean JSON matching this exact schema:
{
  "title": string (required, 1-200 chars),
  "done": boolean (default false),
  "tags": array of strings (optional),
  "priority": "low" | "medium" | "high" (optional)
}
Do NOT add explanations. Return ONLY valid JSON. Do NOT include markdown fences."""


def _build_stub_response(messy_text: str) -> Dict[str, Any]:
    import re
    text = messy_text.strip()
    tags = re.findall(r"#(\w+)", text)
    t = re.sub(r"#\w+", "", text)
    t_lower = t.lower()
    priority = None
    if "urgent" in t_lower or "high" in t_lower:
        priority = "high"
    elif "low" in t_lower:
        priority = "low"
    elif "medium" in t_lower or "mid" in t_lower:
        priority = "medium"
    t = re.sub(r"\b(urgent|high\s*priority|medium\s*priority|low\s*priority|mid\s*priority)\b", "", t, flags=re.I)
    t = " ".join(t.split())
    if not t:
        t = text[:200]
    result = {"title": t[:200], "done": False}
    if tags:
        result["tags"] = tags
    if priority:
        result["priority"] = priority
    return result
def _call_provider(messy_text: str) -> Dict[str, Any]:
    if KILL_SWITCH:
        raise RuntimeError("LLM kill switch is enabled")

    if PROVIDER == "stub":
        start = time.perf_counter()
        res = _build_stub_response(messy_text)
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_cost(MODEL, 0, 0, 0, latency_ms, success=True)
        return res

    # Generic OpenAI-compatible (e.g. OpenRouter)
    url = f"{BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    # Optional headers for OpenRouter
    if "openrouter" in BASE_URL:
        headers.setdefault("HTTP-Referer", "http://localhost:8000")
        headers.setdefault("X-Title", "FlyRank-LLM-Endpoint")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this task text: {messy_text}"},
        ],
        "temperature": TEMPERATURE,
        "response_format": {"type": "json_object"},
    }
    start = time.perf_counter()
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        resp = client.post(url, headers=headers, json=payload)
    latency_ms = int((time.perf_counter() - start) * 1000)
    if resp.status_code >= 400:
        raise httpx.HTTPStatusError(f"Provider error {resp.status_code}: {resp.text}", request=resp.request, response=resp)
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
    except Exception as e:
        raise ValueError(f"Unexpected provider response format: {e}")
    # log cost
    log_cost(MODEL, prompt_tokens, completion_tokens, total_tokens, latency_ms, success=True)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from provider: {e}")
    return parsed


def parse_messy_text(messy_text: str) -> Dict[str, Any]:
    """Parse messy text into validated ParsedTask dict.
    Stage 4: validate schema; on failure, try simple repair/retry concept via re-asking? 
    Keep it simple: call provider, validate with pydantic/jsonschema.
    If fails, do ONE repair attempt by re-prompting for strict JSON.
    """
    if not messy_text or not str(messy_text).strip():
        raise ValueError("messy_text is required and cannot be empty")
    try:
        raw = _call_provider(messy_text)
    except Exception:
        raise
    # Validate
    try:
        obj = ParsedTask.model_validate(raw)
        return obj.model_dump(exclude_none=True)
    except ValidationError as ve:
        # Stage 4: repair attempt
        repair_prompt = (
            f"FIX THIS JSON to match the required schema exactly. Return ONLY valid JSON.\n"
            f"Schema: {{'title': str(1-200), 'done': bool, 'tags': list[str]?, 'priority': 'low'|'medium'|'high'?}}\n"
            f"Broken: {json.dumps(raw)}\n"
            f"Original text: {messy_text}"
        )
        try:
            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": repair_prompt},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
            start = time.perf_counter()
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                resp = client.post(f"{BASE_URL.rstrip('/')}/chat/completions", headers=_repair_headers(), json=payload)
            latency_ms = int((time.perf_counter() - start) * 1000)
            if resp.status_code < 400:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                log_cost(MODEL, usage.get("prompt_tokens",0), usage.get("completion_tokens",0), 
                         usage.get("total_tokens",0), latency_ms, success=True)
                raw2 = json.loads(content)
                obj = ParsedTask.model_validate(raw2)
                return obj.model_dump(exclude_none=True)
        except Exception:
            pass  # fall through
        raise ValueError(f"Schema validation failed: {ve}")


def _repair_headers():
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if "openrouter" in BASE_URL:
        headers.setdefault("HTTP-Referer", "http://localhost:8000")
        headers.setdefault("X-Title", "FlyRank-LLM-Endpoint")
    return headers
