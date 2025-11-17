# ecrf.spec — EXE named 'eCRF-bin' inside folder 'eCRF'; include backend via hiddenimports
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import Tree

# Project root (robust if __file__ missing)
try:
    HERE = Path(__file__).resolve().parent
except NameError:
    import os
    HERE = Path(os.getcwd()).resolve()

# 1) Only tuple-style data in Analysis
analysis_data = []

# Add tzdata if available (safe to skip)
try:
    analysis_data += collect_data_files("tzdata")
except Exception as e:
    print(f"!! tzdata not found; skipping ({e})")

# Ensure PyJWT (module 'jwt') is included
# - submodules for runtime imports
# - distribution metadata for version/runtime checks (if any)
try:
    jwt_submods = collect_submodules("jwt")
    if jwt_submods:
        print(f"++ collected jwt submodules: {len(jwt_submods)}")
except Exception as e:
    print(f"!! could not collect jwt submodules ({e})")
    jwt_submods = []

try:
    analysis_data += copy_metadata("PyJWT")
except Exception as e:
    print(f"!! PyJWT metadata missing ({e})")

try:
    sa_submods = collect_submodules("sqlalchemy")
    if sa_submods:
        print(f"++ collected sqlalchemy submodules: {len(sa_submods)}")
except Exception as e:
    print(f"!! could not collect sqlalchemy submodules ({e})")
    sa_submods = []

hiddenimports = [
    "eCRF_backend",
    "eCRF_backend.main",
    "eCRF_backend.users",
    "eCRF_backend.forms",
    "eCRF_backend.api",
    "eCRF_backend.models",
    "eCRF_backend.schemas",
    "eCRF_backend.database",
    "eCRF_backend.logger",
    "eCRF_backend.crud",
    "eCRF_backend.auth",
    "eCRF_backend.bids_exporter",

    # libs commonly used by FastAPI stacks (harmless if unused)
    "yaml",
    "filelock",

    # force-include PyJWT
    "jwt",
    "sqlalchemy",
] + jwt_submods

# 2) Directory trees for COLLECT
extra_trees = []

def add_tree(rel_path: str, prefix: str):
    p = (HERE / rel_path).resolve()
    if p.exists():
        print(f"++ Including data tree: {p} -> {prefix}")
        extra_trees.append(Tree(str(p), prefix=prefix))
    else:
        print(f"!! Missing data tree: {p} (skipping)")

# Frontend bundle (ensure you've run: cd ecrf_frontend && npm run build)
# support both casings
add_tree("ecrf_frontend/dist", "ecrf_frontend/dist")
add_tree("eCRF_frontend/dist", "eCRF_frontend/dist")

# Backend resources (include templates as server.py references them via ECRF_TEMPLATES_DIR)
add_tree("eCRF_backend/templates", "eCRF_backend/templates")

a = Analysis(
    ["server.py"],
    pathex=[str(HERE), str(HERE / "eCRF_backend")],   # include the backend on sys.path
    binaries=[],
    datas=analysis_data,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# EXE must have a different name than the COLLECT folder
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="eCRF-bin",
    console=True,  # set False to hide the console window
)

dist = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    *extra_trees,          # Trees go here
    strip=False,
    upx=False,
    upx_exclude=[],
    name="eCRF",           # final app folder under dist/
)

# Optional: remove top-level EXE if PyInstaller ever leaves one alongside the folder
import os as _os
from pathlib import Path as _Path

exe_name = "eCRF-bin.exe" if _os.name == "nt" else "eCRF-bin"
top_level_exe = _Path(HERE, "dist", exe_name)

try:
    if top_level_exe.exists():
        top_level_exe.unlink()
        print(f"-- removed top-level EXE: {top_level_exe}")
except Exception as e:
    print(f"!! could not remove {top_level_exe}: {e}")
