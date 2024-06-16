
from pydantic import BaseModel
from typing import Optional


class UserRegistration(BaseModel):
    username: str
    password: str
    email: str
    full_name: str

class UserRegistrationResponse(BaseModel):
    username: str
   
class UserLogin(BaseModel):
    username: str
    password: str

class UserLoginResponse(BaseModel):
     username: str
     access_token: str
     token_type: str = "bearer"
     message: str
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

