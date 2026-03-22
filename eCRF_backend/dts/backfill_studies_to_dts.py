# scripts/backfill_studies_to_dts.py
from eCRF_backend.database import SessionLocal
from eCRF_backend import models
from eCRF_backend.dts.crud_dts import upsert_study_to_dts

db = SessionLocal()

studies = db.query(models.StudyMetadata).all()
for meta in studies:
    content = db.query(models.StudyContent).filter(models.StudyContent.study_id == meta.id).first()
    upsert_study_to_dts(meta, content)
    print(f"Synced study {meta.id}")

db.close()