from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

from repository import create_task
from repository import delete_task as delete_record
from repository import get_task as fetch_task
from repository import get_tasks as fetch_tasks
from repository import init_db
from repository import update_task

from supabase_auth.errors import AuthApiError

from supabase_client import supabase
from llm import parse_messy_text, get_cost_log, clear_cost_log, KILL_SWITCH


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Server running and connected to Supabase")
    yield


app = FastAPI(lifespan=lifespan)


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


class AuthBody(BaseModel):
    email: str = ""
    password: str = ""

class MessyTextParseRequest(BaseModel):
    text: str


class ParsedTaskResponse(BaseModel):
    title: str
    done: bool
    tags: Optional[list[str]] = None
    priority: Optional[str] = None


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    return fetch_tasks()


@app.get("/tasks/{task_id}")
def get_task_by_id(task_id: int):
    task = fetch_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})
    return task


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def post_new_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "title is required"})

    return create_task(task.title.strip())


@app.put("/tasks/{task_id}")
def put_task(task_id: int, update: TaskUpdate):
    if update.title is None and update.done is None:
        raise HTTPException(status_code=400, detail={"error": "nothing to update"})

    title = update.title.strip() if update.title is not None else None
    if title is not None and not title:
        raise HTTPException(status_code=400, detail={"error": "title is required"})

    task = update_task(task_id, title=title, done=update.done)
    if task is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    if not delete_record(task_id):
        raise HTTPException(status_code=404, detail={"error": "Task not found"})


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(body: AuthBody):
    if not body.email.strip() or not body.password:
        raise HTTPException(status_code=400, detail={"error": "email and password are required"})
    try:
        res = supabase.auth.sign_up({"email": body.email.strip(), "password": body.password})
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    return {"user": res.user.model_dump(mode="json")}


@app.post("/auth/login")
def login(body: AuthBody):
    if not body.email.strip() or not body.password:
        raise HTTPException(status_code=400, detail={"error": "email and password are required"})
    try:
        res = supabase.auth.sign_in_with_password({"email": body.email.strip(), "password": body.password})
    except AuthApiError:
        raise HTTPException(status_code=401, detail={"error": "Invalid login credentials"})
    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
    }


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail={"error": "Access token required"})
    try:
        res = supabase.auth.get_user(credentials.credentials)
    except AuthApiError:
        raise HTTPException(status_code=401, detail={"error": "Invalid or expired token"})
    if res is None or res.user is None:
        raise HTTPException(status_code=401, detail={"error": "Invalid or expired token"})
    return res.user


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/protected/dashboard")
def protected_dashboard(user=Depends(get_current_user)):
    return {
        "message": f"Welcome back, {user.email}",
        "stats": {"tasks": len(fetch_tasks())},
    }



@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user=Depends(get_current_user)):
    supabase.auth.sign_out()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/llm/parse", response_model=ParsedTaskResponse)
def parse_messy(messy: MessyTextParseRequest):
    try:
        result = parse_messy_text(messy.text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})


@app.get("/llm/costs")
def llm_costs():
    return {"costs": get_cost_log()}


@app.post("/llm/costs/clear")
def llm_costs_clear():
    clear_cost_log()
    return {"cleared": True}
