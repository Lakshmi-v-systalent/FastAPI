
from pydantic import BaseModel
from typing import Optional

class TodoItem(BaseModel):
    title: str
    description: str = None

class TodoItemResponse(BaseModel):
    id: int
    title: str
    description: str = None

class UpdateTodoItem(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
