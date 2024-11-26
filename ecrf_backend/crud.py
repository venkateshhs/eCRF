from sqlalchemy.orm import Session
from models import User

def get_user_by_username(db: Session, username: str):
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
