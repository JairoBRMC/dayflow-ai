import uuid
from typing import Optional, Type, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from database import Base, get_db
from models import Event, Task
from schemas import (
    EventCreate,
    EventOut,
    EventUpdate,
    Priority,
    TaskCreate,
    TaskOut,
    TaskStatus,
    TaskUpdate,
)

app = FastAPI(title="Dayflow AI")

ModelType = TypeVar("ModelType", bound=Base)


def _get_or_404(model: Type[ModelType], obj_id: uuid.UUID, db: Session) -> ModelType:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


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


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(Task, task_id, db)


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: uuid.UUID, task_update: TaskUpdate, db: Session = Depends(get_db)):
    task = _get_or_404(Task, task_id, db)
    for field, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = _get_or_404(Task, task_id, db)
    db.delete(task)
    db.commit()
    return Response(status_code=204)


@app.post("/events", response_model=EventOut)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    new_event = Event(**event.model_dump())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@app.get("/events", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.start_time).all()


@app.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(Event, event_id, db)


@app.put("/events/{event_id}", response_model=EventOut)
def update_event(event_id: uuid.UUID, event_update: EventUpdate, db: Session = Depends(get_db)):
    event = _get_or_404(Event, event_id, db)
    for field, value in event_update.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    if event.end_time <= event.start_time:
        raise HTTPException(status_code=422, detail="end_time debe ser posterior a start_time")
    db.commit()
    db.refresh(event)
    return event


@app.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    event = _get_or_404(Event, event_id, db)
    db.delete(event)
    db.commit()
    return Response(status_code=204)
