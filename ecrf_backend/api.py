from fastapi import APIRouter
import pytz

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/timezones")
async def get_timezones():
    return list(pytz.all_timezones)

