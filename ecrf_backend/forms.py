import os
import shutil
from typing import List, Dict

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from pathlib import Path
import json
import yaml
from database import get_db
import schemas, crud, models
from logger import logger
from models import User
from users import get_current_user, oauth2_scheme
from fastapi.responses import FileResponse, StreamingResponse
import io
from sqlalchemy.orm import Session

router = APIRouter(prefix="/forms", tags=["forms"])

TEMPLATE_DIR = Path("shacl/templates")  # Path to your templates directory
BASE_DIR = Path(__file__).resolve().parent.parent / "ecrf_backend" /"data_models" / "clinical_study_model"


# @router.get("/study-types")
# def get_study_types():
#     file_path = Path(__file__).parent / "shacl" / "study_type" / "study_type.json"
#     print(file_path)
#     try:
#         with file_path.open("r") as file:
#             data = json.load(file)
#             print(data)
#             return JSONResponse(content=data)
#     except FileNotFoundError:
#         return JSONResponse(content={"error": "File not found"}, status_code=404)
#     except json.JSONDecodeError:
#         return JSONResponse(content={"error": "Invalid JSON format"}, status_code=400)

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


"""
# Currently not used since we are not saving forms separately, rather saving the study as a whole
@router.post("/save-form")
def save_form(
        form_data: dict,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):

    new_form = Form(user_id=user.id, **form_data)
    db.add(new_form)
    db.commit()
    db.refresh(new_form)
    return {"message": "Form saved successfully", "form_id": new_form.id}


@router.get("/saved-forms")
def load_saved_forms(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    forms = db.query(Form).filter(Form.user_id == user.id).all()
    if not forms:
        raise HTTPException(status_code=404, detail="No saved forms found")
    return forms
"""



def load_yaml_file(file_path):
    """Utility function to load a YAML file and return as dictionary."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
"""
This code block has been commented becuase we are no longer rendering the study models from the yaml file since its not necessary to "label" each study. User can select each study
by selecting from the drop down and then constructing the study from the form generation. This way users have the full freedom to create a study.


@router.get("/models")
def get_study_models(user: User = Depends(get_current_user)):
   
    logger.info(f"User {user.username} is accessing study models.")

    # Debug BASE_DIR
    print(f"\n Debug: Checking BASE_DIR: {BASE_DIR}")

    if not BASE_DIR.exists():
        print(f" ERROR: BASE_DIR does not exist: {BASE_DIR}")
        raise HTTPException(status_code=500, detail="Server configuration error: BASE_DIR missing.")

    study_models = {}

    # Debugging categories inside BASE_DIR
    category_dirs = list(BASE_DIR.iterdir())
    print(f" Found categories: {category_dirs}")

    if not category_dirs:
        raise HTTPException(status_code=404, detail="No study models found (empty BASE_DIR).")

    for category in category_dirs:
        if category.is_dir():
            category_name = category.name
            study_models[category_name] = {}

            yaml_files = list(category.glob("*.yaml"))
            print(f" Category '{category_name}' - YAML Files Found: {yaml_files}")

            if not yaml_files:
                print(f" WARNING: No YAML files found in {category_name}")

            for yaml_file in yaml_files:
                model_data = load_yaml_file(yaml_file)
                if model_data:
                    study_models[category_name][yaml_file.stem] = model_data
                else:
                    print(f" WARNING: Failed to load {yaml_file}")

    if not study_models:
        raise HTTPException(status_code=404, detail="No study models found")

    return study_models
"""

"""
# doesnt make sense to call an api to just to get file names from yaml files, this has been changed to  get the study type and description
# from a study_types.json file from public folder. 
@router.get("/case-studies", response_model=List[Dict[str, str]])
def get_case_study_names(user: dict = Depends(get_current_user)):

    if not BASE_DIR.exists():
        raise HTTPException(status_code=500, detail="Server configuration error: BASE_DIR missing.")

    case_studies = []

    yaml_files = list(BASE_DIR.glob("*.yaml"))
    if not yaml_files:
        raise HTTPException(status_code=404, detail="No case studies found.")

    for yaml_file in yaml_files:
        data = load_yaml_file(yaml_file)

        if not data or "classes" not in data:
            continue  # Skip files without proper structure

        # Extract name from file name
        study_name = yaml_file.stem.replace("_", " ").title()

        # Get the first class description
        class_data = next(iter(data["classes"].values()), {})
        study_description = class_data.get("description", "No description available.")

        case_studies.append({
            "name": study_name,
            "description": study_description
        })

    return case_studies


NO longer used since since we are not specifying the study type and its structure, rather just using yaml names to indicate
the study type as a meta information
@router.get("/models/{category}/{file_name}")
def get_yaml_content(category: str, file_name: str, user: User = Depends(get_current_user)):
    # Fetch and return the structured content of a YAML file.
    logger.info(f"User {user.username} is accessing {file_name} in {category}")

    category_path = BASE_DIR / category
    if not category_path.exists() or not category_path.is_dir():
        raise HTTPException(status_code=404, detail="Category not found")

    yaml_path = category_path / f"{file_name}.yaml"
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    yaml_content = load_yaml_file(yaml_path)
    if not yaml_content:
        raise HTTPException(status_code=500, detail="Error loading YAML file")

    return yaml_content  # Send parsed YAML structure
"""

"""
@router.get("/{form_id}")
def get_form_by_id(
    form_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    form = db.query(Form).filter(Form.id == form_id, Form.user_id == user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form
"""

@router.post("/studies/", response_model=schemas.StudyFull)
def create_study(
    study_metadata: schemas.StudyMetadataCreate,
    study_content: schemas.StudyContentCreate,
    db: Session = Depends(get_db)
):
    try:
        metadata, content = crud.create_study(db, study_metadata, study_content)
    except Exception as e:
        logger.error("Error creating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"metadata": metadata, "content": content}

@router.get("/studies", response_model=List[schemas.StudyMetadataOut])
def list_studies(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    studies = db.query(models.StudyMetadata).all()
    return studies

@router.get("/studies/{study_id}", response_model=schemas.StudyFull)
def read_study(study_id: int, db: Session = Depends(get_db)):
    result = crud.get_study_full(db, study_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Study not found")
    metadata, content = result
    return {"metadata": metadata, "content": content}

@router.put("/studies/{study_id}", response_model=schemas.StudyFull)
def update_study(
    study_id: int,
    metadata_update: schemas.StudyMetadataUpdate,
    content_update: schemas.StudyContentUpdate,
    db: Session = Depends(get_db)
):
    try:
        result = crud.update_study(db, study_id, metadata_update, content_update)
    except Exception as e:
        logger.error("Error updating study: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Study not found")
    metadata, content = result
    return {"metadata": metadata, "content": content}

@router.get("/studies/{study_id}/files", response_model=List[schemas.FileOut])
def read_files_for_study(study_id: int, db: Session = Depends(get_db)):
    files = crud.get_files_for_study(db, study_id)
    return files

@router.post("/studies/{study_id}/files", response_model=schemas.FileOut)
def upload_file(
    study_id: int,
    uploaded_file: UploadFile = File(...),
    description: str = Form(""),
    storage_option: str = Form("local"),
    db: Session = Depends(get_db)
):
    try:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_location = os.path.join(upload_dir, uploaded_file.filename)
        with open(file_location, "wb") as f:
            shutil.copyfileobj(uploaded_file.file, f)
    except Exception as e:
        logger.error("File upload error: %s", e)
        raise HTTPException(status_code=500, detail="Error saving file")
    try:
        file_data = schemas.FileCreate(
            study_id=study_id,
            file_name=uploaded_file.filename,
            file_path=file_location,
            description=description,
            storage_option=storage_option
        )
        db_file = crud.create_file(db, file_data)
    except Exception as e:
        logger.error("Error creating file record: %s", e)
        raise HTTPException(status_code=500, detail="Error creating file record")
    return db_file
