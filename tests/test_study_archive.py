import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from eCRF_backend import forms_hybrid, models, schemas
from eCRF_backend.database import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def add_user(db, username: str, role: str):
    user = models.User(username=username, email=f"{username}@example.org", password="hashed")
    db.add(user)
    db.flush()
    db.add(
        models.UserProfile(
            user_id=user.id,
            first_name=username.title(),
            last_name="User",
            role=role,
        )
    )
    db.commit()
    db.refresh(user)
    return user


def add_study(db, owner_id: int, status: str = "PUBLISHED"):
    study = models.StudyMetadata(
        created_by=owner_id,
        study_name="Archive test",
        study_description="Regression fixture",
        status=status,
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return study


def test_archived_study_permissions_are_view_only_for_owner(db):
    owner = add_user(db, "owner", "Principal Investigator")
    study = add_study(db, owner.id, status="ARCHIVED")

    assert forms_hybrid._effective_study_permissions(db, study, owner) == {
        "view": True,
        "add_data": False,
        "edit_study": False,
    }

    with pytest.raises(HTTPException) as exc:
        forms_hybrid._assert_has_study_permission(db, study, owner, required="add_data")
    assert exc.value.status_code == 409
    assert exc.value.detail == "Archived studies are read-only"


def test_archive_and_unarchive_restore_previous_status(db):
    owner = add_user(db, "owner", "Principal Investigator")
    study = add_study(db, owner.id, status="DRAFT")

    archived = forms_hybrid.archive_study(study.id, db=db, user=owner)
    assert archived["status"] == "ARCHIVED"
    assert archived["archived_from_status"] == "DRAFT"
    assert archived["permissions"]["edit_study"] is False

    restored = forms_hybrid.unarchive_study(study.id, db=db, user=owner)
    assert restored["status"] == "DRAFT"
    assert restored["archived_from_status"] is None
    assert restored["permissions"]["edit_study"] is True


def test_only_owner_or_admin_can_archive(db):
    owner = add_user(db, "owner", "Principal Investigator")
    outsider = add_user(db, "outsider", "Investigator")
    study = add_study(db, owner.id)

    with pytest.raises(HTTPException) as exc:
        forms_hybrid.archive_study(study.id, db=db, user=outsider)
    assert exc.value.status_code == 403


def test_only_owner_or_admin_can_unarchive(db):
    owner = add_user(db, "owner", "Principal Investigator")
    outsider = add_user(db, "outsider", "Investigator")
    study = add_study(db, owner.id, status="ARCHIVED")

    with pytest.raises(HTTPException) as exc:
        forms_hybrid.unarchive_study(study.id, db=db, user=outsider)
    assert exc.value.status_code == 403
    db.refresh(study)
    assert study.status == "ARCHIVED"


def test_admin_can_archive_another_users_study(db):
    owner = add_user(db, "owner", "Principal Investigator")
    admin = add_user(db, "admin", "Administrator")
    study = add_study(db, owner.id)

    archived = forms_hybrid.archive_study(study.id, db=db, user=admin)
    assert archived["status"] == "ARCHIVED"

    restored = forms_hybrid.unarchive_study(study.id, db=db, user=admin)
    assert restored["status"] == "PUBLISHED"


def test_owner_can_save_enrollment_plan_and_remove_it(db):
    owner = add_user(db, "owner", "Principal Investigator")
    study = add_study(db, owner.id, status="DRAFT")
    content = models.StudyContent(study_id=study.id, study_data={"subjects": []})
    db.add(content)
    db.commit()

    result = forms_hybrid.update_enrollment_plan(
        study.id,
        schemas.EnrollmentPlanUpdate(mode="linear", target_subjects=120, duration_months=12),
        db=db,
        current_user=owner,
    )
    assert result["enrollment_plan"] == {
        "mode": "linear",
        "target_subjects": 120,
        "duration_months": 12,
        "monthly_enrollments": [],
    }
    db.refresh(content)
    assert content.study_data["studySettings"]["enrollmentMonitoring"]["target_subjects"] == 120

    forms_hybrid.update_enrollment_plan(
        study.id,
        schemas.EnrollmentPlanUpdate(mode="none"),
        db=db,
        current_user=owner,
    )
    db.refresh(content)
    assert "enrollmentMonitoring" not in content.study_data["studySettings"]


def test_enrollment_plan_requires_edit_permission_and_writable_study(db):
    owner = add_user(db, "owner", "Principal Investigator")
    outsider = add_user(db, "outsider", "Investigator")
    study = add_study(db, owner.id, status="DRAFT")
    db.add(models.StudyContent(study_id=study.id, study_data={"subjects": []}))
    db.commit()
    payload = schemas.EnrollmentPlanUpdate(mode="monthly", monthly_enrollments=[2, 3, 4])

    with pytest.raises(HTTPException) as unauthorized:
        forms_hybrid.update_enrollment_plan(study.id, payload, db=db, current_user=outsider)
    assert unauthorized.value.status_code == 403

    study.status = "ARCHIVED"
    db.commit()
    with pytest.raises(HTTPException) as archived:
        forms_hybrid.update_enrollment_plan(study.id, payload, db=db, current_user=owner)
    assert archived.value.status_code == 409
