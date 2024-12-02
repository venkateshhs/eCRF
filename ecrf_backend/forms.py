from fastapi import APIRouter, HTTPException, Depends, Query
from pathlib import Path
import json

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