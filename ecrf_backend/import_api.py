# routes_import.py
import io
import logging
from typing import Optional, Literal, Dict, Any, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse

# If you use auth, uncomment next line and add Depends(get_current_user)
# from users import get_current_user

import pandas as pd

# BIDS (optional)
try:
    from bids import BIDSLayout  # type: ignore
    HAS_PYBIDS = True
except Exception:
    HAS_PYBIDS = False

logger = logging.getLogger("import")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/import", tags=["import"])

# ---- helpers -----------------------------------------------------------------

CANDIDATES = {
    "subject": ["subject", "participant", "participant_id", "sub", "sub_id", "subjectid", "id"],
    "visit":   ["visit", "session", "timepoint", "tp", "ses", "visit_no", "visitnum"],
    "group":   ["group", "arm", "cohort", "treatmentgroup", "grp"],
    "assignment": ["assignment", "randomization", "treatment", "armassigned", "assigned_group"],
}

def _best_match(columns: List[str], keys: List[str]) -> Optional[str]:
    cols = [c.strip() for c in columns]
    lower = {c.lower(): c for c in cols}
    for k in keys:
        if k in lower:
            return lower[k]
    # soft contains
    for c in cols:
        cl = c.lower()
        for k in keys:
            if k in cl:
                return c
    return None

def infer_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    return {
        "subject": _best_match(columns, CANDIDATES["subject"]),
        "visit": _best_match(columns, CANDIDATES["visit"]),
        "group": _best_match(columns, CANDIDATES["group"]),
        "assignment": _best_match(columns, CANDIDATES["assignment"]),
    }

def dataframe_preview(df: pd.DataFrame, limit: int = 10) -> Dict[str, Any]:
    # Replace NaN for JSON serialization
    sample = df.head(limit).fillna("").astype(str).to_dict(orient="records")
    return {
        "columns": list(df.columns),
        "rows": sample,
        "total_rows": int(df.shape[0]),
        "total_cols": int(df.shape[1]),
    }

# ---- route -------------------------------------------------------------------

@router.post("/preview")
async def import_preview(
    # study_id is optional; default to -1 and log that we’re in “ad-hoc” mode
    study_id: Optional[int] = Form(None),
    kind: Literal["csv", "excel", "bids"] = Form(...),
    file: UploadFile = File(...),
    # CSV/Excel options
    delimiter: Optional[str] = Form(","),
    has_header: Optional[bool] = Form(True),
) -> JSONResponse:
    effective_study_id = study_id if study_id is not None else -1
    logger.info("[/import/preview] kind=%s, study_id=%s, filename=%s",
                kind, effective_study_id, file.filename)

    if kind in ("csv", "excel"):
        content = await file.read()
        try:
            if kind == "csv":
                logger.info("Parsing CSV (delimiter=%s, header=%s)", delimiter, has_header)
                if has_header:
                    df = pd.read_csv(io.BytesIO(content), sep=delimiter or ",", dtype=str, engine="python")
                else:
                    df = pd.read_csv(io.BytesIO(content), sep=delimiter or ",", header=None, dtype=str, engine="python")
                    # add generic column names if no header
                    df.columns = [f"col_{i+1}" for i in range(df.shape[1])]
            else:
                logger.info("Parsing Excel")
                df = pd.read_excel(io.BytesIO(content), dtype=str)

            prev = dataframe_preview(df)
            mapping = infer_mapping(prev["columns"])
            # Remaining columns become study_data fields
            mapped_cols = {c for c in mapping.values() if c}
            other_columns = [c for c in prev["columns"] if c not in mapped_cols]

            logger.info("Inferred mapping: %s; other_columns=%s", mapping, other_columns)

            return JSONResponse({
                "ok": True,
                "study_id": effective_study_id,
                "kind": kind,
                "preview": prev,
                "mapping": mapping,
                "other_columns": other_columns,
                "message": "Preview generated",
            })
        except Exception as e:
            logger.exception("Failed to parse %s: %s", kind, e)
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    elif kind == "bids":
        if not HAS_PYBIDS:
            logger.error("PyBIDS not installed")
            raise HTTPException(400, "PyBIDS is not installed on the server")
        # For preview, we don’t ingest the file; we just indicate we can scan a BIDS folder
        logger.info("BIDS preview requested; expecting a zipped dataset or path (not implemented).")
        raise HTTPException(400, "BIDS preview not implemented in this endpoint yet")

    raise HTTPException(400, "Unsupported kind")
