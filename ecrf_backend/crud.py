import os

from sqlalchemy.orm import Session

import schemas, models
from models import User
from logger import logger

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


def create_study(db: Session, study: schemas.StudyCreate, user_id: int):
    db_study = models.Study(
        user_id=user_id,
        name=study.name,
        description=study.description,
        number_of_subjects=study.number_of_subjects,
        number_of_visits=study.number_of_visits,
        meta_info=study.meta_info,
    )
    db.add(db_study)
    db.commit()
    db.refresh(db_study)
    for form in study.forms:
         db_form = models.Form(
             study_id=db_study.id,
             form_name=form.form_name,  # Use dot notation
             sections=form.sections
         )
         db.add(db_form)
    db.commit()
    db.refresh(db_study)
    return db_study



def create_study_file(db: Session, study_id: int, file_name: str, file_data: bytes, content_type: str,
                      storage_option: str = "db", description: str = None):
    if storage_option == "db":
        db_file = models.StudyFile(
            study_id=study_id,
            file_name=file_name,
            file_data=file_data,
            file_path=None,
            content_type=content_type,
            storage_type="db",
            description=description,
        )
    elif storage_option == "local":
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_location = os.path.join(upload_dir, file_name)
        with open(file_location, "wb") as f:
            f.write(file_data)
        db_file = models.StudyFile(
            study_id=study_id,
            file_name=file_name,
            file_data=None,
            file_path=file_location,
            content_type=content_type,
            storage_type="local",
            description=description,
        )
    else:
        raise ValueError("Invalid storage option provided. Use 'db' or 'local'.")

    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


def get_study(db: Session, study_id: int):
    return db.query(models.Study).filter(models.Study.id == study_id).first()