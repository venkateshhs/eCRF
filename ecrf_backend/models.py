from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, LargeBinary, JSON, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    studies = relationship("Study", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class FormShape(Base):
    __tablename__ = "form_shapes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # Form name
    description = Column(Text, nullable=True)  # Optional form description
    shape = Column(JSON, nullable=False)


class Study(Base):
    __tablename__ = "studies"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Link to creator
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    number_of_subjects = Column(Integer, nullable=True)
    number_of_visits = Column(Integer, nullable=True)
    meta_info = Column(JSON, nullable=True)

    # One study has many forms and many files.
    forms = relationship("Form", back_populates="study", cascade="all, delete")
    files = relationship("StudyFile", back_populates="study", cascade="all, delete")

    user = relationship("User", back_populates="studies")


class Form(Base):
    __tablename__ = "forms"
    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("studies.id"), nullable=False)
    form_name = Column(String, nullable=False)
    sections = Column(JSON, nullable=True)  # Nested sections and fields as JSON

    # Each form belongs to one study.
    study = relationship("Study", back_populates="forms")


class StudyFile(Base):
    __tablename__ = "study_files"
    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("studies.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=True)  # Used if file is stored in DB
    file_path = Column(String, nullable=True)  # Used if file is stored on local disk
    content_type = Column(String, nullable=True)  # MIME type (optional)
    storage_type = Column(String, default="db")  # "db" or "local"
    description = Column(Text, nullable=True)

    # Each file belongs to one study.
    study = relationship("Study", back_populates="files")
