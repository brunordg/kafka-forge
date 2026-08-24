from app.services import kafka_service, operation_log


def test_logs_route_starts_empty(api_client):
    response = api_client.get("/api/v1/logs")

    assert response.status_code == 200
    assert response.json() == []


def test_logs_route_returns_recorded_operations(api_client):
    operation_log.append_operation_record(
        operation_log.OperationType.TESTE_CONEXAO,
        operation_log.OperationResult.SUCESSO,
        duracao_ms=42,
        configuracao="Desenvolvimento",
    )

    response = api_client.get("/api/v1/logs")

    assert response.status_code == 200
    [record] = response.json()
    assert record["tipo_operacao"] == "teste_conexao"
    assert record["resultado"] == "sucesso"
    assert record["configuracao"] == "Desenvolvimento"
    assert record["duracao_ms"] == 42


def test_logs_route_filters_by_tipo_and_resultado(api_client):
    operation_log.append_operation_record(
        operation_log.OperationType.TESTE_CONEXAO,
        operation_log.OperationResult.SUCESSO,
        duracao_ms=1,
    )
    operation_log.append_operation_record(
        operation_log.OperationType.PUBLICACAO,
        operation_log.OperationResult.ERRO,
        duracao_ms=2,
        erro_tecnico="falha simulada",
    )

    response = api_client.get("/api/v1/logs", params={"resultado": "erro"})

    assert response.status_code == 200
    [record] = response.json()
    assert record["tipo_operacao"] == "publicacao"
    assert record["erro_tecnico"] == "falha simulada"


def test_logs_route_is_documented_in_openapi_schema(api_client):
    response = api_client.get("/openapi.json")

    paths = response.json()["paths"]
    assert "get" in paths["/api/v1/logs"]
