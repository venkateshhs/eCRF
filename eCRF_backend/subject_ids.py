"""Validate newly enrolled subjects without rewriting historical identities."""
import re

from fastapi import HTTPException


def validate_new_subject_ids(study_data, existing_subjects=()):
    subjects = (study_data or {}).get("subjects") or []
    if not isinstance(subjects, list):
        raise HTTPException(status_code=400, detail="Subjects must be a list")
    config = (study_data or {}).get("subjectIdConfig") or {}
    manual = config.get("mode") == "manual" or config.get("preset") == "manual"
    seen = {str(s.get("id") or s.get("subject_id") or "").strip().lower() for s in existing_subjects}
    duplicates = {}
    for subject in subjects[len(existing_subjects):]:
        if not isinstance(subject, dict):
            raise HTTPException(status_code=400, detail="Each subject must have an ID")
        identifier = str(subject.get("id") or subject.get("subject_id") or "").strip()
        if not identifier:
            raise HTTPException(status_code=400, detail="Each subject must have an ID")
        if manual and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", identifier):
            raise HTTPException(status_code=400, detail="Subject IDs must contain 1–128 letters, numbers, hyphens or underscores, starting with a letter or number")
        if identifier.lower() in seen:
            duplicates.setdefault(identifier.lower(), identifier)
        seen.add(identifier.lower())
    if duplicates:
        labels = ", ".join(f'"{identifier}"' for identifier in duplicates.values())
        raise HTTPException(
            status_code=400,
            detail=f"The following Subject IDs are duplicated or already exist: {labels}. No subjects were added.",
        )
