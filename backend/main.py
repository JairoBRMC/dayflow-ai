import uuid
from typing import Optional, Type, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database import Base, get_db
from models import ChatMessage, Conversation, Event, Task, User
from schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    EventCreate,
    EventOut,
    EventUpdate,
    MessageOut,
    Priority,
    RefreshRequest,
    TaskCreate,
    TaskOut,
    TaskStatus,
    TaskUpdate,
    Token,
    UserCreate,
    UserOut,
)

app = FastAPI(title="Dayflow AI")

ModelType = TypeVar("ModelType", bound=Base)


def _get_owned_or_404(model: Type[ModelType], obj_id: uuid.UUID, owner_id: uuid.UUID, db: Session) -> ModelType:
    """Busca un registro por id perteneciente a owner_id. 404 si no existe O si es de otro
    usuario -- así nadie puede distinguir "no existe" de "existe pero no es tuyo"."""
    obj = db.query(model).filter(model.id == obj_id, model.user_id == owner_id).first()
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=user.email, hashed_password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@app.post("/auth/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(payload.refresh_token, expected_type="refresh")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="No se pudo validar las credenciales")
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@app.post("/tasks", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_task = Task(**task.model_dump(), user_id=current_user.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[Priority] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task).filter(Task.user_id == current_user.id)
    if status is not None:
        query = query.filter(Task.status == status)
    if priority is not None:
        query = query.filter(Task.priority == priority)
    return query.order_by(Task.created_at.desc()).all()


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_owned_or_404(Task, task_id, current_user.id, db)


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_or_404(Task, task_id, current_user.id, db)
    for field, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_owned_or_404(Task, task_id, current_user.id, db)
    db.delete(task)
    db.commit()
    return Response(status_code=204)


@app.post("/events", response_model=EventOut)
def create_event(event: EventCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_event = Event(**event.model_dump(), user_id=current_user.id)
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@app.get("/events", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Event)
        .filter(Event.user_id == current_user.id)
        .order_by(Event.start_time)
        .all()
    )


@app.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_owned_or_404(Event, event_id, current_user.id, db)


@app.put("/events/{event_id}", response_model=EventOut)
def update_event(
    event_id: uuid.UUID,
    event_update: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = _get_owned_or_404(Event, event_id, current_user.id, db)
    for field, value in event_update.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    if event.end_time <= event.start_time:
        raise HTTPException(status_code=422, detail="end_time debe ser posterior a start_time")
    db.commit()
    db.refresh(event)
    return event


@app.delete("/events/{event_id}", status_code=204)
def delete_event(
    event_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    event = _get_owned_or_404(Event, event_id, current_user.id, db)
    db.delete(event)
    db.commit()
    return Response(status_code=204)


@app.post("/conversations", response_model=ConversationOut)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = Conversation(title=payload.title, user_id=current_user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@app.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


@app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = _get_owned_or_404(Conversation, conversation_id, current_user.id, db)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[MessageOut.model_validate(message) for message in messages],
    )


@app.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = _get_owned_or_404(Conversation, conversation_id, current_user.id, db)
    db.delete(conversation)
    db.commit()
    return Response(status_code=204)
