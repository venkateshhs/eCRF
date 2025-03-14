from pydantic import BaseModel, EmailStr, constr
from typing import Dict, Any, Optional, List


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
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


# NO Longer required
class FormShapeCreate(BaseModel):
    name: str
    description: Optional[str]
    shape: Dict[str, Any]  # SHACL Shape

class FormShapeResponse(FormShapeCreate):
    id: int

    class Config:
        from_attributes = True


class FormSaveSchema(BaseModel):
    form_name: str
    form_structure: Any

    class Config:
        from_attributes = True


class FormSchema(BaseModel):
    id: int
    user_id: int
    form_name: str
    form_structure: Any

    class Config:
        from_attributes = True


class FormBase(BaseModel):
    form_name: str
    sections: Optional[Any] = None


class Form(FormBase):
    id: int

    class Config:
        from_attributes = True


class StudyFile(BaseModel):
    id: int
    file_name: str
    content_type: Optional[str] = None
    storage_type: str
    file_path: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class StudyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    number_of_subjects: Optional[int] = None
    number_of_visits: Optional[int] = None
    meta_info: Optional[dict] = None
    forms: List[FormBase]


class Study(BaseModel):
    id: int
    name: str
    description: Optional[str]
    number_of_subjects: Optional[int]
    number_of_visits: Optional[int]
    meta_info: Optional[dict]
    forms: List[Form]
    files: List[StudyFile] = []

    class Config:
        from_attributes = True
