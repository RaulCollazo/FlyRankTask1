from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import sqlite3


app = FastAPI()

tasks_db = sqlite3.connect("task.db", check_same_thread=False)
tasks_db.row_factory = sqlite3.Row


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
    cursor = tasks_db.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    return [dict(task) for task in tasks]


@app.get("/tasks/{task_id}")
def get_task_by_id(task_id: int):
    cursor = tasks_db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?" , (task_id,))
    tasks = cursor.fetchone()
    if tasks is None: 
        raise HTTPException(status_code=404, detail={"error": f"Task {task_id} not found"})
    return dict(tasks)
    


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def post_new_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "title is required"})

    cursor = tasks_db.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task.title.strip(), False),
    )
    tasks_db.commit()
    new_task = {"id": cursor.lastrowid, "title": task.title.strip(), "done": False}
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