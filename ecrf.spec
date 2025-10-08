# ecrf.spec — EXE named 'eCRF-bin' inside folder 'eCRF'; include backend via hiddenimports
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import Tree

# Project root (robust if __file__ missing)
try:
    HERE = Path(__file__).resolve().parent
except NameError:
    import os
    HERE = Path(os.getcwd()).resolve()

# 1) Only tuple-style datas in Analysis
analysis_datas = []
hiddenimports = [
    "yaml",
    "filelock",
    # ensure backend package is bundled (dynamic import in server.py)
    "ecrf_backend",
    "ecrf_backend.main",
    "ecrf_backend.users",
    "ecrf_backend.forms",
    "ecrf_backend.api",
    "ecrf_backend.models",
    "ecrf_backend.schemas",
    "ecrf_backend.database",
    "ecrf_backend.logger",
    "ecrf_backend.crud",
    "ecrf_backend.auth",
    "ecrf_backend.bids_exporter",
]

# tzdata is useful on Windows/minimal Linux for zoneinfo. OK to skip on macOS.
try:
    analysis_datas += collect_data_files("tzdata")
except Exception as e:
    print(f"!! tzdata not found; skipping ({e})")

# 2) Directory trees for COLLECT
extra_trees = []

def add_tree(rel_path: str, prefix: str):
    p = (HERE / rel_path).resolve()
    if p.exists():
        print(f"++ Including data tree: {p} -> {prefix}")
        extra_trees.append(Tree(str(p), prefix=prefix))
    else:
        print(f"!! Missing data tree: {p} (skipping)")

# Frontend bundle (ensure you've run: cd eCRF_frontend && npm run build)
add_tree("eCRF_frontend/dist", "eCRF_frontend/dist")
# Backend resources
add_tree("ecrf_backend/shacl/templates", "ecrf_backend/shacl/templates")
add_tree("ecrf_backend/data_models", "ecrf_backend/data_models")

a = Analysis(
    ["server.py"],
    pathex=[str(HERE)],
    binaries=[],
    datas=analysis_datas,   # tuples only
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
    *extra_trees,     # Trees go here
    strip=False,
    upx=False,
    upx_exclude=[],
    name="eCRF",      # final app folder under dist/
)
