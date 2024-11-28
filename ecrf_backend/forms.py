from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import FormShape
from schemas import FormShapeCreate, FormShapeResponse
import json

router = APIRouter(prefix="/forms", tags=["forms"])


@router.post("/", response_model=FormShapeResponse)
def create_form_shape(form: FormShapeCreate, db: Session = Depends(get_db)):
    """
    Create a new form template in the database.
    """
    existing_form = db.query(FormShape).filter(FormShape.name == form.name).first()
    if existing_form:
        raise HTTPException(status_code=400, detail="Form with this name already exists.")

    new_form = FormShape(name=form.name, description=form.description, shape=form.shape)
    db.add(new_form)
    db.commit()
    db.refresh(new_form)
    return new_form


@router.get("/", response_model=list[FormShapeResponse])
def list_form_shapes(db: Session = Depends(get_db)):
    """
    Retrieve all available form templates from the database.
    """
    return db.query(FormShape).all()


@router.get("/{form_id}", response_model=FormShapeResponse)
def get_form_shape(form_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific form template by its ID.
    """
    form = db.query(FormShape).filter(FormShape.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found.")
    return form


@router.put("/{form_id}", response_model=FormShapeResponse)
def update_form_shape(form_id: int, form: FormShapeCreate, db: Session = Depends(get_db)):
    """
    Update an existing form template.
    """
    existing_form = db.query(FormShape).filter(FormShape.id == form_id).first()
    if not existing_form:
        raise HTTPException(status_code=404, detail="Form not found.")

    existing_form.name = form.name
    existing_form.description = form.description
    existing_form.shape = form.shape
    db.commit()
    db.refresh(existing_form)
    return existing_form


@router.delete("/{form_id}")
def delete_form_shape(form_id: int, db: Session = Depends(get_db)):
    """
    Delete a specific form template.
    """
    form = db.query(FormShape).filter(FormShape.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found.")
    db.delete(form)
    db.commit()
    return {"message": "Form deleted successfully"}


@router.post("/validate")
def validate_form_submission(form_data: dict, form_id: int, db: Session = Depends(get_db)):
    """
    Validate form data against its SHACL template.
    """
    form = db.query(FormShape).filter(FormShape.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found.")

    # Load the SHACL shape from the form
    shape = json.loads(form.shape)

    # Validate data (add actual SHACL validation logic here)
    # For now, we'll return a simple validation result
    validation_result = {"valid": True, "message": "Form data is valid."}

    return validation_result


@router.post("/save")
def save_form_data(form_data: dict, form_id: int, db: Session = Depends(get_db)):
    """
    Save submitted form data for reproducibility and future editing.
    """
    form = db.query(FormShape).filter(FormShape.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found.")

    # For now, save form data to a local JSON file (or a database in production)
    file_name = f"saved_form_{form_id}.json"
    with open(file_name, "w") as f:
        json.dump(form_data, f)

    return {"message": "Form data saved successfully", "file": file_name}
