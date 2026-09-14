from fastapi import FastAPI

app = FastAPI()


tasks_db = [[1,"walk",True],[2,"pet the dog",False],[3,"watch youtube", True]]

@app.get("/")
async def root():
    return { "name": "Task API", "version": "1.0", "endpoints": ["/tasks"] }

@app.get("/health")
def health():
    return {"status" : "ok"}

@app.get("/tasks")
def gwet_tasks():
    return tasks_db

@app.get("/tasks/{task_id}")
def get_task_by_id(task_id : int):
    for task in tasks_db:
        if task[0] == task_id:
            return task
    raise HTTPException(status_code=404, detail={ "error": "Task 99 not found" })

@app.post("/tasks")
def post_new_task(title: str , content: str):
    tasks_db.append([len(tasks_db) +1 ,title,content]) 
    return tasks_db