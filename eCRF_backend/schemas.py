from datetime import datetime
from typing import Any, Optional, Dict, List, Literal

from pydantic import BaseModel, EmailStr, constr, Field


class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr


class UserProfileBase(BaseModel):
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)
    role: constr(min_length=1, max_length=30)


class UserCreate(UserBase, UserProfileBase):
    password: constr(min_length=8)


class AdminUserCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=8)
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)
    role: constr(min_length=1, max_length=50)

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: int
    profile: UserProfileBase

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=8)
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)


# -------------------- Study Metadata / Content --------------------

class StudyMetadataBase(BaseModel):
    study_name: str
    study_description: Optional[str] = None

    #  workflow fields (optional to avoid regressions)
    status: Optional[str] = None                 # "DRAFT" | "PUBLISHED" | "ARCHIVED"
    draft_of_study_id: Optional[int] = None      # if this is an edit-draft of an existing study
    last_completed_step: Optional[int] = None    # wizard resume helper


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
    subject_index: Optional[int] = None
    visit_index: Optional[int] = None
    group_index: Optional[int] = None


class FileOut(FileBase):
    id: int
    study_id: int
    created_at: datetime
    subject_index: Optional[int] = None
    visit_index: Optional[int] = None
    group_index: Optional[int] = None

    class Config:
        from_attributes = True


# Pydantic model that accepts arbitrary fields
class SettingsModel(BaseModel):
    model_config = {"extra": "allow"}

# Pydantic models for output (and input)


class EventOut(BaseModel):
    id: int
    study_id: Optional[int]
    subject_id: Optional[int]
    user: Optional[UserResponse]    # nested user info (who did it)
    action: str
    timestamp: datetime
    details: Dict[str, Any]

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    study_id: Optional[int] = None
    subject_id: Optional[int] = None
    user_id: int    # ID of the user/agent performing the action
    action: str
    details: Optional[Dict[str, Any]] = None


class ShareLinkCreate(BaseModel):
    study_id: int
    subject_index: int
    visit_index: int
    group_index: int
    permission: Literal["view", "add"] = "view"
    max_uses: int = Field(1, gt=0)
    expires_in_days: int = Field(7, gt=0)


class SharedFormAccessOut(BaseModel):
    study_id: int
    subject_index: int
    visit_index: int
    group_index: int
    permission: str
    study: Any

    class Config:
        from_attributes = True


# -------------------- Study Template Versions --------------------
# Avoid shadowing BaseModel.schema by naming the attribute differently
# and exposing it on the wire as "schema" via aliases.

class StudyTemplateVersionBase(BaseModel):
    version: int
    template_schema: Any = Field(
        default_factory=dict,
        validation_alias="schema",
        serialization_alias="schema",
    )

    class Config:
        from_attributes = True


class StudyTemplateVersionCreate(StudyTemplateVersionBase):
    pass


class StudyTemplateVersionOut(StudyTemplateVersionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------- Data Entry --------------------

class StudyDataEntryCreate(BaseModel):
    # study_id comes from the path (/studies/{study_id}/data)
    subject_index: int
    visit_index: int
    group_index: int
    data: Dict[str, Any] = Field(default_factory=dict)
    skipped_required_flags: Optional[List[List[bool]]]


class StudyDataEntryOut(BaseModel):
    id: int
    study_id: int
    form_version: int
    subject_index: int
    visit_index: int
    group_index: int
    data: Dict[str, Any]
    skipped_required_flags: Optional[List[List[bool]]]
    created_at: datetime

    class Config:
        from_attributes = True


class StudyDataEntryUpdate(BaseModel):
    data: Optional[Dict[str, Any]] = None
    skipped_required_flags: Optional[List[List[bool]]] = None


class PaginatedStudyDataEntries(BaseModel):
    total: int
    entries: List[StudyDataEntryOut]

    class Config:
        from_attributes = True


class SharedStudyDataEntryCreate(BaseModel):
    data: Dict[str, Any]
    skipped_required_flags: Optional[Dict[str, Any]] = None


# -------------------- Access Grants --------------------

class StudyAccessGrantCreate(BaseModel):
    user_id: int
    role: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None


class StudyAccessGrantOut(BaseModel):
    user_id: int
    role: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    created_by: Optional[int] = None
    created_by_display: Optional[str] = None
    created_at: datetime
    permissions: Dict[str, bool]

    class Config:
        from_attributes = True

class RoleUpdate(BaseModel):
    role: constr(min_length=1, max_length=50)



class BulkPayload(BaseModel):
    entries: List[StudyDataEntryCreate]