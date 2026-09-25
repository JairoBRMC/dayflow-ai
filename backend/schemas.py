import uuid
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

Priority = Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[Priority] = "medium"
    due_date: Optional[date] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[date]
