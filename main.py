from fastapi import FastAPI, HTTPException, status

app = FastAPI()

tasks_db = [[1, "walk", True], [2, "pet the dog", False], [3, "watch youtube", True]]

@app.get("/")
async def root():
    return { "name": "Task API", "version": "1.0", "endpoints": ["/tasks"] }

@app.get("/health")
def health():
    return {"status" : "ok"}

@app.get("/tasks")
def get_tasks():
    return tasks_db

@app.get("/tasks/{task_id}")
def get_task_by_id(task_id: int):
    for task in tasks_db:
        if task[0] == task_id:
            return task
    raise HTTPException(status_code=404, detail={ "error": "Task not found" })

@app.post("/tasks")
def post_new_task(title: str, content: bool):
    new_id = tasks_db[-1][0] + 1 if tasks_db else 1
    tasks_db.append([new_id, title, content]) 
    return tasks_db

@app.put("/tasks/{task_id}")
def put_new_task(task_id: int, title: str = None, done: bool = False):
    for tarea in tasks_db:
        if tarea[0] == task_id:
            if title is not None:
                tarea[1] = title
            tarea[2] = done
            return tarea
    raise HTTPException(status_code=404, detail={ "error": "Task not found" })

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    for tarea in tasks_db:
        if tarea[0] == task_id:
            tasks_db.remove(tarea)
            return tasks_db
    raise HTTPException(status_code=404, detail={ "error": "Unknown id" })
