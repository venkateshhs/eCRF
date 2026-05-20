from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, SavedFormTemplate
from .schemas import SavedFormTemplateOut, SavedFormTemplateCreate, SavedFormTemplateUpdate
from .users import get_current_user

router = APIRouter(
    prefix="/forms/saved-templates",
    tags=["Saved Form Templates"],
)


def _is_admin_user(user: User) -> bool:
    role = getattr(getattr(user, "profile", None), "role", "") or ""
    return str(role).strip().lower() == "admin"


@router.post(
    "",
    response_model=SavedFormTemplateOut,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_form_template(
    payload: SavedFormTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save a reusable form template.

    Even if frontend saves only selected section(s), send them wrapped like:
    {
      "form_schema": {
        "sections": [...]
      },
      "source_type": "section_subset"
    }
    """

    sections = payload.form_schema.get("sections")

    if not isinstance(sections, list) or len(sections) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="form_schema.sections must contain at least one section.",
        )

    template = SavedFormTemplate(
        title=payload.title.strip(),
        description=payload.description.strip(),
        form_schema=payload.form_schema,
        source_type=payload.source_type,
        created_by=current_user.id,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get(
    "",
    response_model=List[SavedFormTemplateOut],
)
def list_saved_form_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    All authenticated users can retrieve saved templates,
    because saved templates are reusable across users.
    """

    return (
        db.query(SavedFormTemplate)
        .order_by(SavedFormTemplate.updated_at.desc(), SavedFormTemplate.created_at.desc())
        .all()
    )


@router.get(
    "/{template_id}",
    response_model=SavedFormTemplateOut,
)
def get_saved_form_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(SavedFormTemplate)
        .filter(SavedFormTemplate.id == template_id)
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved form template not found.",
        )

    return template


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_saved_form_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(SavedFormTemplate)
        .filter(SavedFormTemplate.id == template_id)
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved form template not found.",
        )

    is_owner = template.created_by == current_user.id
    is_admin = _is_admin_user(current_user)

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator or an admin can delete this saved template.",
        )

    db.delete(template)
    db.commit()

    return None

@router.patch(
    "/{template_id}",
    response_model=SavedFormTemplateOut,
)
def update_saved_form_template(
    template_id: int,
    payload: SavedFormTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(SavedFormTemplate)
        .filter(SavedFormTemplate.id == template_id)
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved form template not found.",
        )

    is_owner = template.created_by == current_user.id
    is_admin = _is_admin_user(current_user)

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator or an admin can update this saved template.",
        )

    if payload.title is not None:
        template.title = payload.title.strip()

    if payload.description is not None:
        template.description = payload.description.strip()

    if payload.source_type is not None:
        template.source_type = payload.source_type

    if payload.form_schema is not None:
        sections = payload.form_schema.get("sections")

        if not isinstance(sections, list) or len(sections) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="form_schema.sections must contain at least one section.",
            )

        template.form_schema = payload.form_schema

    db.commit()
    db.refresh(template)

    return template