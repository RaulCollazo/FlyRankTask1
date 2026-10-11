# Task API

## LLM Parse Endpoint (W7)

This API includes an LLM-backed endpoint that takes messy task text and returns clean, validated JSON.

### Endpoint
POST /llm/parse

Request:
```json
{
  "text": "buy milk tomorrow #urgent"
}
```

Response (validated):
```json
{
  "title": "buy milk tomorrow",
  "done": false,
  "tags": ["urgent"],
  "priority": "high"
}
```

### Other LLM endpoints
- GET /llm/costs - View cost/latency/token log
- POST /llm/costs/clear - Clear cost log

### Configuration (.env)
- LLM_PROVIDER (stub|openrouter|openai) - default: stub
- LLM_KILL_SWITCH (true/false) - disable calls if true
- LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY
- LLM_COST_PER_1K_TOKENS_IN/OUT for cost tracking
- LLM_MODEL, LLM_BASE_URL, LLM_API_KEY

### Run with stub (no API key needed)
```bash
curl -X POST http://localhost:8000/llm/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"urgent finish report #work"}'
```

### Eval
Run the eval script:
```bash
python -c "
import json
from llm import parse_messy_text, clear_cost_log
clear_cost_log()
with open('eval.json') as f:
    cases = json.load(f)['cases']
passed = sum(1 for c in cases if all(k in (r:=parse_messy_text(c['input'])) for k in ['title']) and isinstance(r['done'],bool))
print('score', passed, '/', len(cases))
"
```
