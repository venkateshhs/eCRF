"""Validate newly enrolled subjects without rewriting historical identities."""
import unicodedata

from fastapi import HTTPException


def _subject_id_key(value):
    return unicodedata.normalize("NFC", str(value or "").strip()).lower()


def _valid_manual_subject_id(value):
    identifier = unicodedata.normalize("NFC", str(value or "").strip())
    return (
        1 <= len(identifier) <= 128
        and identifier[0].isalnum()
        and all(character.isalnum() or character in "_-" for character in identifier)
    )


def validate_new_subject_ids(study_data, existing_subjects=()):
    subjects = (study_data or {}).get("subjects") or []
    if not isinstance(subjects, list):
        raise HTTPException(status_code=400, detail="Subjects must be a list")
    config = (study_data or {}).get("subjectIdConfig") or {}
    manual = config.get("mode") == "manual" or config.get("preset") == "manual"
    seen = {_subject_id_key(s.get("id") or s.get("subject_id") or "") for s in existing_subjects}
    duplicates = {}
    for subject in subjects[len(existing_subjects):]:
        if not isinstance(subject, dict):
            raise HTTPException(status_code=400, detail="Each subject must have an ID")
        identifier = str(subject.get("id") or subject.get("subject_id") or "").strip()
        if not identifier:
            raise HTTPException(status_code=400, detail="Each subject must have an ID")
        if manual and not _valid_manual_subject_id(identifier):
            raise HTTPException(status_code=400, detail="Subject IDs must contain 1–128 letters, numbers, hyphens or underscores, starting with a letter or number")
        normalized = _subject_id_key(identifier)
        if normalized in seen:
            duplicates.setdefault(normalized, identifier)
        seen.add(normalized)
    if duplicates:
        labels = ", ".join(f'"{identifier}"' for identifier in duplicates.values())
        raise HTTPException(
            status_code=400,
            detail=f"The following Subject IDs are duplicated or already exist: {labels}. No subjects were added.",
        )
