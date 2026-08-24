SIMPLE_AVSC = (
    '{"type": "record", "name": "Pedido", "namespace": "com.example", '
    '"fields": [{"name": "id", "type": "long"}, {"name": "cliente", "type": "string"}]}'
)


def test_validate_schema_route_returns_name_namespace_and_fields_for_a_valid_avsc(api_client):
    response = api_client.post("/api/v1/schema/validate", json={"avsc_content": SIMPLE_AVSC})

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["nome"] == "Pedido"
    assert body["namespace"] == "com.example"
    assert body["fields"] == [
        {"nome": "id", "tipo": "long"},
        {"nome": "cliente", "tipo": "string"},
    ]


def test_validate_schema_route_returns_a_structured_error_for_malformed_json(api_client):
    response = api_client.post(
        "/api/v1/schema/validate", json={"avsc_content": "{isso nao eh json valido"}
    )

    # não é um 500 genérico: sucesso HTTP com um resultado estruturado
    # indicando valid=False e uma mensagem compreensível
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["message"]
    assert body["nome"] is None


def test_validate_schema_route_returns_a_structured_error_for_a_semantically_invalid_avro_schema(
    api_client,
):
    response = api_client.post(
        "/api/v1/schema/validate",
        json={"avsc_content": '{"type": "record", "name": "Pedido"}'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert "incompleta" in body["message"].lower()


def test_validate_schema_route_with_empty_avsc_content_returns_422_with_an_understandable_message(
    api_client,
):
    response = api_client.post("/api/v1/schema/validate", json={"avsc_content": "   "})

    assert response.status_code == 422
    assert "conteúdo do arquivo .avsc" in response.text


def test_schema_route_is_documented_in_openapi_schema(api_client):
    response = api_client.get("/openapi.json")

    paths = response.json()["paths"]
    assert "post" in paths["/api/v1/schema/validate"]
