from pydantic import BaseModel, EmailStr, constr
from typing import Dict, Any, Optional

class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr

class UserProfileBase(BaseModel):
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)

class UserCreate(UserBase, UserProfileBase):
    password: constr(min_length=8)

class UserResponse(UserBase):
    id: int
    profile: UserProfileBase

    class Config:
        orm_mode = True

class LoginRequest(BaseModel):
    username: str
    password: str


class FormShapeCreate(BaseModel):
    name: str
    description: Optional[str]
    shape: Dict[str, Any]  # SHACL Shape

class FormShapeResponse(FormShapeCreate):
    id: int

    class Config:
        orm_mode = True