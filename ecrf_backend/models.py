import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, JSON, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Update relationship to reference StudyMetadata instead of Study
    studies = relationship("StudyMetadata", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    role = Column(String(20), nullable=False, server_default="Investigator")

    user = relationship("User", back_populates="profile")


class StudyMetadata(Base):
    __tablename__ = "study_metadata"

    id = Column(Integer, primary_key=True, index=True)
    # Make created_by a ForeignKey referencing users.id
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    study_name = Column(String(255), nullable=False)
    study_description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship back to User
    user = relationship("User", back_populates="studies")
    # One-to-one relationship with StudyContent
    content = relationship("StudyContent", uselist=False, back_populates="study_metadata", cascade="all, delete")
    shared_links = relationship("SharedFormAccess", back_populates="study", cascade="all, delete-orphan")
    entry_data = relationship("StudyEntryData", back_populates="study", cascade="all, delete-orphan")
    template_versions = relationship("StudyTemplateVersion", back_populates="study", cascade="all, delete-orphan")

class StudyContent(Base):
    __tablename__ = "study_content"
    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("study_metadata.id", ondelete="CASCADE"), unique=True, nullable=False)
    study_data = Column(JSON)  # JSON structure that contains metaInfo and forms
    study_metadata = relationship("StudyMetadata", back_populates="content")

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("study_metadata.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # e.g. URL or file system path
    description = Column(Text)
    storage_option = Column(String(50))  # e.g., 'local' or 'db'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

"""
Table for user settings/configuration
"""
class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id = Column(Integer, primary_key=True, index=True)
    settings = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class SharedFormAccess(Base):
    __tablename__ = "shared_form_access"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False)
    study_id = Column(Integer, ForeignKey("study_metadata.id"), nullable=False)
    subject_index = Column(Integer, nullable=False)
    visit_index = Column(Integer, nullable=False)
    group_index = Column(Integer, nullable=False)
    permission = Column(String(10), default="view")  # "view" or "add"
    max_uses = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    study = relationship("StudyMetadata", back_populates="shared_links")

class StudyTemplateVersion(Base):
    __tablename__ = "study_template_versions"

    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("study_metadata.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    schema = Column(JSON, nullable=False)  # Full form structure with constraints
    created_at = Column(DateTime, server_default=func.now())

    study = relationship("StudyMetadata", back_populates="template_versions")


class StudyEntryData(Base):
    __tablename__ = "study_entry_data"

    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("study_metadata.id", ondelete="CASCADE"), nullable=False)
    form_version = Column(Integer, nullable=False)
    subject_index = Column(Integer, nullable=False)
    visit_index = Column(Integer, nullable=False)
    group_index = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)  # Actual field data per form instance
    created_at = Column(DateTime, server_default=func.now())
    skipped_required_flags = Column(JSON, nullable=True)

    study = relationship("StudyMetadata", back_populates="entry_data")
