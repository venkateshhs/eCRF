# tests/test_datalad_patch_import.py
def test_patch_module_imports():
    import eCRF_backend.datalad_patch as m
    assert hasattr(m, "install_datalad_audit_hooks")
