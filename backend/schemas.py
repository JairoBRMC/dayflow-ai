import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator

Priority = Literal["low", "medium", "high"]
TaskStatus = Literal["pending", "in_progress", "done"]


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[Priority] = "medium"
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    due_date: Optional[date] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[date]


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def check_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time debe ser posterior a start_time")
        return self


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
