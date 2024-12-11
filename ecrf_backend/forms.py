from typing import List

from fastapi import APIRouter, HTTPException, Depends, Query
from pathlib import Path
import json

from database import get_db
from logger import logger
from schemas import FormSchema, FormSaveSchema
from models import Form, User
from users import get_current_user, oauth2_scheme

from sqlalchemy.orm import Session
router = APIRouter(prefix="/forms", tags=["forms"])

TEMPLATE_DIR = Path("shacl/templates")  # Path to your templates directory


@router.get("/templates")
def list_templates():
    """
    List all available SHACL templates.
    """
    templates = [f.name for f in TEMPLATE_DIR.glob("*.json")]
    print(templates)
    return {"templates": templates}


@router.get("/templates/shacl")
def get_shacl_template(template_name: str = Query(None)):
    """
    Load and return the selected SHACL template by name.
    """
    if not template_name:
        raise HTTPException(status_code=400, detail="No template selected.")

    template_path = TEMPLATE_DIR / template_name

    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found.")

    with open(template_path, "r") as template_file:
        try:
            template = json.load(template_file)
            return template
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Error reading template file.")



@router.get("/available-fields")
async def get_available_fields():
    try:
        # Load the JSON file dynamically from the templates directory
        available_fields_file = TEMPLATE_DIR / "available-fields.json"
        if not available_fields_file.exists():
            raise HTTPException(status_code=404, detail="Available fields file not found.")

        with open(available_fields_file, "r") as file:
            data = json.load(file)

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading available fields: {str(e)}")


@router.get("/specialized-fields")
async def get_specialized_fields():
    try:
        # Load the JSON file dynamically from the templates directory
        available_fields_file = TEMPLATE_DIR / "specialized-fields.json"
        if not available_fields_file.exists():
            raise HTTPException(status_code=404, detail="Available fields file not found.")

        with open(available_fields_file, "r") as file:
            data = json.load(file)

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading available fields: {str(e)}")



@router.post("/save-form")
def save_form(
    form_data: FormSaveSchema,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),  # Extract token from the Authorization header
):
    current_user = get_current_user(token, db)
    logger.info(f"Saving form: {form_data}")
    logger.info(f"Current user: {current_user}")

    form = Form(
        user_id=current_user.id,
        form_name=form_data.form_name,
        form_structure=form_data.form_structure,
    )
    db.add(form)
    db.commit()
    db.refresh(form)

    logger.info(f"Form saved successfully: {form}")
    return form


@router.get("/load-saved-forms", response_model=list[FormSchema])
def load_saved_forms(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        # Query forms associated with the logged-in user
        forms = db.query(Form).filter(Form.user_id == current_user.id).all()

        # Debugging: Log the retrieved forms
        logger.info(f"Forms retrieved for user {current_user.id}: {forms}")

        return forms
    except Exception as e:
        logger.error(f"Error loading saved forms: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading saved forms: {str(e)}")