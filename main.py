from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

tasks_db = [
    {"id": 1, "title": "walk", "done": True},
    {"id": 2, "title": "pet the dog", "done": False},
    {"id": 3, "title": "watch youtube", "done": True},
]


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    return tasks_db


@app.get("/tasks/{task_id}")
def get_task_by_id(task_id: int):
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail={"error": f"Task {task_id} not found"})


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def post_new_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "title is required"})

    new_id = tasks_db[-1]["id"] + 1 if tasks_db else 1
    new_task = {"id": new_id, "title": task.title.strip(), "done": False}
    tasks_db.append(new_task)
    return new_task


@app.put("/tasks/{task_id}")
def put_task(task_id: int, update: TaskUpdate):
    if update.title is None and update.done is None:
        raise HTTPException(status_code=400, detail={"error": "nothing to update"})

    if update.title is not None and not update.title.strip():
        raise HTTPException(status_code=400, detail={"error": "title cannot be empty"})

    for task in tasks_db:
        if task["id"] == task_id:
            if update.title is not None:
                task["title"] = update.title.strip()
            if update.done is not None:
                task["done"] = update.done
            return task

    raise HTTPException(status_code=404, detail={"error": f"Task {task_id} not found"})


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    for task in tasks_db:
        if task["id"] == task_id:
            tasks_db.remove(task)
            return

    raise HTTPException(status_code=404, detail={"error": f"Task {task_id} not found"})