from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from database import get_db
from models import Task
from schemas import TaskCreate, TaskOut

app = FastAPI(title="Dayflow AI")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = Task(**task.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task
