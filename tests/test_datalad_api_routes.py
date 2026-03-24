# tests/test_datalad_api_routes.py
def test_router_imports():
    from eCRF_backend.datalad_api_routes import router
    assert router.prefix == "/datalad"
