from fastapi import APIRouter, Depends, HTTPException
import pytz
from sqlalchemy.orm import Session

from .database import get_db, SessionLocal
from .models import UserSettings
from .schemas import SettingsModel


router = APIRouter(prefix="/api", tags=["api"])

@router.get("/timezones")
async def get_timezones():
    return list(pytz.all_timezones)


@router.post("/settings/{user_id}")
def save_settings(user_id: int, settings_data: SettingsModel, db: Session = Depends(get_db)):
    settings_dict = settings_data.model_dump()

    # Query for existing settings for this user
    user_setting = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if user_setting:
        user_setting.settings = settings_dict
    else:
        user_setting = UserSettings(user_id=user_id, settings=settings_dict)
        db.add(user_setting)
    db.commit()
    return {"message": "Settings saved successfully."}

@router.get("/settings/{user_id}")
def get_user_settings(user_id: int, db: Session = Depends(get_db)):
    user_setting = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if user_setting is None:
        raise HTTPException(status_code=404, detail="Settings not found")
    return user_setting.settings