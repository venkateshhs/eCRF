from datetime import datetime
from pydantic import BaseModel, EmailStr, constr
from typing import Any, Optional


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


# Study Metadata Schemas
class StudyMetadataBase(BaseModel):
    study_name: str
    study_description: Optional[str] = None


class StudyMetadataCreate(StudyMetadataBase):
    created_by: int


class StudyMetadataUpdate(StudyMetadataBase):
    pass


class StudyMetadataOut(StudyMetadataBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Study Content Schemas
class StudyContentBase(BaseModel):
    study_data: Optional[Any] = None  # dynamic JSON structure


class StudyContentCreate(StudyContentBase):
    pass


class StudyContentUpdate(StudyContentBase):
    pass


class StudyContentOut(StudyContentBase):
    id: int
    study_id: int

    class Config:
        from_attributes = True


# Combined Study Schema
class StudyFull(BaseModel):
    metadata: StudyMetadataOut
    content: StudyContentOut

    class Config:
        from_attributes = True


# File Schemas
class FileBase(BaseModel):
    file_name: str
    file_path: str
    description: Optional[str] = None
    storage_option: Optional[str] = None


class FileCreate(FileBase):
    study_id: int


class FileOut(FileBase):
    id: int
    study_id: int
    created_at: datetime

    class Config:
        from_attributes = True
