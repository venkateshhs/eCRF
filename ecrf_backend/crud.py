import os
from sqlalchemy.orm import Session
from datetime import datetime
import schemas, models
from models import User
from logger import logger
from zoneinfo import ZoneInfo

def get_user_by_username(db: Session, username: str):
    logger.debug(f"Fetching user by username: {username}")
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data, hashed_password: str):
    from models import User, UserProfile
    user = User(username=user_data.username, email=user_data.email, password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return user

def create_study(db: Session, metadata: schemas.StudyMetadataCreate, content: schemas.StudyContentCreate):
    try:
        db_metadata = models.StudyMetadata(
            created_by=metadata.created_by,
            study_name=metadata.study_name,
            study_description=metadata.study_description
        )
        db.add(db_metadata)
        db.commit()
        db.refresh(db_metadata)
    except Exception as e:
        db.rollback()
        raise Exception(f"Error creating study metadata: {e}")

    try:
        db_content = models.StudyContent(
            study_id=db_metadata.id,
            study_data=content.study_data
        )
        db.add(db_content)
        db.commit()
        db.refresh(db_content)
    except Exception as e:
        db.rollback()
        db.delete(db_metadata)
        db.commit()
        raise Exception(f"Error creating study content: {e}")

    return db_metadata, db_content

def get_study_full(db: Session, study_id: int):
    metadata = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not metadata:
        return None
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    return metadata, content

def update_study(db: Session, study_id: int, metadata_update: schemas.StudyMetadataUpdate, content_update: schemas.StudyContentUpdate):
    db_metadata = db.query(models.StudyMetadata).filter(models.StudyMetadata.id == study_id).first()
    if not db_metadata:
        return None
    try:
        for key, value in metadata_update.dict(exclude_unset=True).items():
            setattr(db_metadata, key, value)
        db_metadata.updated_at = datetime.now(ZoneInfo("Europe/Paris"))
        db.commit()
        db.refresh(db_metadata)
    except Exception as e:
        db.rollback()
        raise Exception(f"Error updating study metadata: {e}")

    db_content = db.query(models.StudyContent).filter(models.StudyContent.study_id == study_id).first()
    if db_content and content_update.study_data is not None:
        try:
            setattr(db_content, "study_data", content_update.study_data)
            db.commit()
            db.refresh(db_content)
        except Exception as e:
            db.rollback()
            raise Exception(f"Error updating study content: {e}")

    return db_metadata, db_content

def create_file(db: Session, file_data: schemas.FileCreate):
    try:
        db_file = models.File(
            study_id=file_data.study_id,
            file_name=file_data.file_name,
            file_path=file_data.file_path,
            description=file_data.description,
            storage_option=file_data.storage_option
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
    except Exception as e:
        db.rollback()
        raise Exception(f"Error creating file record: {e}")
    return db_file

def get_files_for_study(db: Session, study_id: int):
    return db.query(models.File).filter(models.File.study_id == study_id).all()
