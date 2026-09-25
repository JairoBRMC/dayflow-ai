import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from models import Task
from schemas import Priority, TaskCreate, TaskOut, TaskStatus, TaskUpdate

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


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[Priority] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status is not None:
        query = query.filter(Task.status == status)
    if priority is not None:
        query = query.filter(Task.priority == priority)
    return query.order_by(Task.created_at.desc()).all()


def _get_task_or_404(task_id: uuid.UUID, db: Session) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_task_or_404(task_id, db)


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: uuid.UUID, task_update: TaskUpdate, db: Session = Depends(get_db)):
    task = _get_task_or_404(task_id, db)
    for field, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = _get_task_or_404(task_id, db)
    db.delete(task)
    db.commit()
    return Response(status_code=204)
