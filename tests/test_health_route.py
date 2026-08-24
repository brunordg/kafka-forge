from pathlib import Path


def test_health_endpoint_returns_ok(api_client):
    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_is_registered_under_api_v1_prefix(api_client):
    response = api_client.get("/health")

    assert response.status_code == 404


def test_health_endpoint_is_documented_in_openapi_schema(api_client):
    response = api_client.get("/openapi.json")

    schema = response.json()
    assert "/api/v1/health" in schema["paths"]
    assert "get" in schema["paths"]["/api/v1/health"]


def test_docs_page_is_available(api_client):
    response = api_client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text


def test_main_has_a_single_router_inclusion_point():
    # Guarda-corrim da DoD: novas rotas em api/routes/ devem ser
    # registradas no agregador `app/api/routes/__init__.py`, nunca
    # exigindo um segundo `include_router(...)` em main.py.
    main_source = (Path(__file__).resolve().parent.parent / "app" / "main.py").read_text()

    assert main_source.count(".include_router(") == 1
