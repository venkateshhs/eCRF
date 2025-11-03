import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


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

    # Relationship back to audit events (one-to-many)
    events = relationship("AuditEvent", back_populates="user")


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

    subject_index = Column(Integer, nullable=True)
    visit_index = Column(Integer, nullable=True)
    group_index = Column(Integer, nullable=True)

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
    subject_index = Column(Integer, nullable=False)
    visit_index = Column(Integer, nullable=False)
    group_index = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)  # Actual field data per form instance
    created_at = Column(DateTime, server_default=func.now())
    skipped_required_flags = Column(JSON, nullable=True)

    study = relationship("StudyMetadata", back_populates="entry_data")
    form_version = Column(Integer, nullable=False, default=1)

class StudyAccessGrant(Base):
    __tablename__ = "study_access_grants"
    __table_args__ = (
        UniqueConstraint("study_id", "user_id", name="uq_study_user_access"),
    )

    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("study_metadata.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # JSON of booleans, e.g. {"view": true, "add_data": true, "edit_study": false}
    permissions = Column(JSON, nullable=False, default={"view": True, "add_data": True, "edit_study": False})

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    study = relationship("StudyMetadata", backref="access_grants")
    user = relationship("User", foreign_keys=[user_id])
    granted_by = relationship("User", foreign_keys=[created_by])

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    # If an event is about a Study as a whole, subject_id stays NULL. If it's about a specific subject, both study_id and subject_id are set.
    study_id = Column(Integer, nullable=True, index=True)
    subject_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)  # JSON column to store event details (flexible schema)

    # Relationships
    user = relationship("User", back_populates="events")