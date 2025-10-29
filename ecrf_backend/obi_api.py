# ecrf_backend/api/obi_api.py
"""
OBI ontology search API (fast, deduped).

- Prefers local: ecrf_backend/templates/obi.obo.txt
- Fallback: http://purl.obolibrary.org/obo/obi.obo
- Parses [Term] only, skips obsolete
- DE-DUPS by ID with merge (synonyms union, longest definition)
"""

import time
from pathlib import Path
from typing import Dict, List, Optional

import logging
import re
import requests
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/ontology/obi", tags=["ontology-obi"])

# ---- logging ----
from .logger import logger

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_OBI_PATH = REPO_ROOT / "templates" / "obi.obo.txt"
REMOTE_OBI_URL = "http://purl.obolibrary.org/obo/obi.obo"

TERMS: List[Dict] = []
TERM_INDEX: Dict[str, Dict] = {}
META: Dict[str, str] = {"source": "", "loaded_at": ""}

# Robust regex for OBO bits
ID_RE = re.compile(r"^id:\s*(\S+)")
NAME_RE = re.compile(r"^name:\s*(.+)")
DEF_RE = re.compile(r'^def:\s*"([^"]*)"')
OBSOLETE_RE = re.compile(r"^is_obsolete:\s*true", re.I)
# Handles: synonym: "text" EXACT [XREF:] OR exact_synonym: "text"
SYN_RE_ANY = re.compile(
    r'^(?:synonym|exact_synonym|related_synonym|broad_synonym|narrow_synonym):\s*"([^"]+)"',
    re.I,
)

def _read_obo_text() -> str:
    if LOCAL_OBI_PATH.exists():
        META["source"] = "local"
        try:
            text = LOCAL_OBI_PATH.read_text(encoding="utf-8", errors="ignore")
            logger.info("Loaded OBI from local file: %s (%d chars)", LOCAL_OBI_PATH, len(text))
            return text
        except Exception as e:
            logger.exception("Failed reading local OBI file, falling back to remote: %s", e)

    logger.info("Fetching OBI from remote: %s", REMOTE_OBI_URL)
    try:
        resp = requests.get(REMOTE_OBI_URL, timeout=30)
        resp.raise_for_status()
        text = resp.text
        META["source"] = "remote"
        logger.info("Fetched OBI from remote (%d chars). Caching locally at %s", len(text), LOCAL_OBI_PATH)
        try:
            LOCAL_OBI_PATH.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_OBI_PATH.write_text(text, encoding="utf-8")
        except Exception as e:
            logger.warning("Could not cache remote OBI locally: %s", e)
        return text
    except requests.RequestException as e:
        logger.exception("Remote OBI fetch failed")
        raise HTTPException(status_code=503, detail=f"Failed to load OBI: {e}")

def _parse_obo(text: str) -> List[Dict]:
    """
    Parse OBO into unique terms by ID. When duplicates appear (imports),
    we merge:
      - keep first non-empty name
      - choose longest definition
      - union synonyms
    Only keep IDs starting with OBI:
    """
    start = time.time()
    by_id: Dict[str, Dict] = {}
    current: Optional[Dict] = None
    in_term = False
    obsolete = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line == "[Term]":
            # flush previous
            if in_term and current and not obsolete:
                tid = (current.get("id") or "").strip()
                name = (current.get("name") or "").strip()
                if tid and name and tid.upper().startswith("OBI:"):
                    if tid in by_id:
                        existing = by_id[tid]
                        if not existing.get("name") and name:
                            existing["name"] = name
                        if len((current.get("def") or "")) > len((existing.get("def") or "")):
                            existing["def"] = current.get("def") or ""
                        ex_syn = set(existing.get("synonyms") or [])
                        cur_syn = set(filter(None, (current.get("synonyms") or [])))
                        existing["synonyms"] = sorted(ex_syn.union(cur_syn))
                    else:
                        by_id[tid] = {
                            "id": tid,
                            "name": name,
                            "def": current.get("def") or "",
                            "synonyms": sorted(set(current.get("synonyms") or [])),
                        }
            # new stanza
            current = {"id": "", "name": "", "def": "", "synonyms": []}
            in_term = True
            obsolete = False
            continue

        if not in_term or current is None:
            continue

        if OBSOLETE_RE.match(line):
            obsolete = True
            continue

        m = ID_RE.match(line)
        if m:
            current["id"] = m.group(1).strip()
            continue

        m = NAME_RE.match(line)
        if m:
            current["name"] = m.group(1).strip()
            continue

        m = DEF_RE.match(line)
        if m:
            current["def"] = (m.group(1) or "").strip()
            continue

        m = SYN_RE_ANY.match(line)
        if m:
            syn = m.group(1).strip()
            if syn:
                current["synonyms"].append(syn)
            continue

    # flush last term
    if in_term and current and not obsolete:
        tid = (current.get("id") or "").strip()
        name = (current.get("name") or "").strip()
        if tid and name and tid.upper().startswith("OBI:"):
            if tid in by_id:
                existing = by_id[tid]
                if not existing.get("name") and name:
                    existing["name"] = name
                if len((current.get("def") or "")) > len((existing.get("def") or "")):
                    existing["def"] = current.get("def") or ""
                ex_syn = set(existing.get("synonyms") or [])
                cur_syn = set(filter(None, (current.get("synonyms") or [])))
                existing["synonyms"] = sorted(ex_syn.union(cur_syn))
            else:
                by_id[tid] = {
                    "id": tid,
                    "name": name,
                    "def": current.get("def") or "",
                    "synonyms": sorted(set(current.get("synonyms") or [])),
                }

    took = time.time() - start
    logger.info("Parsed OBI: %d unique OBI:* terms (%.2fs)", len(by_id), took)
    return list(by_id.values())

def _load_terms_if_needed():
    if TERMS:
        return
    t0 = time.time()
    text = _read_obo_text()
    unique_terms = _parse_obo(text)
    TERMS.extend(unique_terms)
    TERM_INDEX.clear()
    for t in TERMS:
        TERM_INDEX[t["id"]] = t
    META["loaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    logger.info("Loaded %d terms into memory (source=%s) in %.2fs",
                len(TERMS), META.get("source", "?"), time.time() - t0)

def _score_match(q: str, term: Dict) -> int:
    ql = q.lower()
    score = 0
    name = term.get("name", "").lower()
    if ql in name:
        score += 100
    for syn in term.get("synonyms") or []:
        if ql in syn.lower():
            score += 60
            break
    if ql in term.get("id", "").lower():
        score += 20
    if ql in (term.get("def") or "").lower():
        score += 10
    return score

@router.get("/search")
def search_terms(
    query: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1),
) -> Dict:
    _load_terms_if_needed()
    q = (query or "").strip()
    if not q:
        return {"count": 0, "source": META.get("source", ""), "results": []}

    start = time.time()
    scored = []
    for t in TERMS:
        s = _score_match(q, t)
        if s > 0:
            scored.append((s, t["name"].lower(), t))

    scored.sort(key=lambda x: (-x[0], x[1], x[2]["id"]))
    out = []
    seen_ids = set()
    for _, _, t in scored:
        if t["id"] in seen_ids:
            continue
        seen_ids.add(t["id"])
        out.append(
            {
                "id": t["id"],
                "name": t["name"],
                "def": t.get("def") or "",
                "synonyms": t.get("synonyms") or [],
            }
        )
        if len(out) >= limit:
            break

    took = (time.time() - start) * 1000.0
    logger.info(
        'Search query="%s" limit=%d matches=%d returned=%d source=%s (%.1f ms)',
        q, limit, len(scored), len(out), META.get("source", ""), took
    )

    return {"count": len(out), "source": META.get("source", ""), "results": out}

@router.get("/meta")
def meta() -> Dict:
    _load_terms_if_needed()
    return {
        "terms": len(TERMS),
        "source": META.get("source", ""),
        "loaded_at": META.get("loaded_at", ""),
        "local_path": str(LOCAL_OBI_PATH),
    }
