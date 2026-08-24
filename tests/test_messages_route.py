from app.config.models import EnvironmentConfiguration, KafkaConfig, SecurityProtocol
from app.services import kafka_service

SIMPLE_AVSC = (
    '{"type": "record", "name": "Pedido", "fields": '
    '[{"name": "id", "type": "long"}, {"name": "valor", "type": "double"}]}'
)


class _FakeProducer:
    class _FakeMessage:
        def __init__(self, partition: int, offset: int):
            self._partition = partition
            self._offset = offset

        def partition(self) -> int:
            return self._partition

        def offset(self) -> int:
            return self._offset

    def __init__(self, *, partition: int = 2, offset: int = 12345):
        self._partition = partition
        self._offset = offset

    def produce(self, topic, value=None, key=None, on_delivery=None):
        if on_delivery is not None:
            on_delivery(None, self._FakeMessage(self._partition, self._offset))

    def flush(self, timeout=None) -> int:
        return 0


def _create_configuration(nome: str = "Desenvolvimento") -> None:
    kafka_service.create_configuration(
        EnvironmentConfiguration(
            nome=nome,
            kafka=KafkaConfig(bootstrap_servers="localhost:9092", security_protocol=SecurityProtocol.PLAINTEXT),
        )
    )


def test_validate_payload_route_returns_valid_for_a_compatible_payload(api_client):
    response = api_client.post(
        "/api/v1/messages/validate",
        json={"avsc_content": SIMPLE_AVSC, "payload": {"id": 1, "valor": 10.5}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["problems"] == []


def test_validate_payload_route_returns_the_same_field_type_error_shape_used_by_the_ui(
    api_client,
):
    # cenário 2 de US-003a / FR-013: campo, tipo esperado, tipo recebido
    # — o mesmo formato de dicionário produzido por
    # services/kafka_service.py::validate_payload e consumido tanto pela
    # UI quanto pela API (NFR-006)
    response = api_client.post(
        "/api/v1/messages/validate",
        json={"avsc_content": SIMPLE_AVSC, "payload": {"id": 1, "valor": "nao-e-numero"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["problems"] == [
        {"campo": "valor", "tipo_esperado": "double", "tipo_recebido": "string"}
    ]


def test_validate_payload_route_returns_a_structured_error_for_a_malformed_schema(api_client):
    response = api_client.post(
        "/api/v1/messages/validate",
        json={"avsc_content": "{isso nao eh json valido", "payload": {"id": 1}},
    )

    # não é um 500 genérico: sucesso HTTP com um resultado estruturado
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["message"]
    assert body["problems"] == []


def test_validate_payload_route_with_empty_avsc_content_returns_422(api_client):
    response = api_client.post(
        "/api/v1/messages/validate", json={"avsc_content": "   ", "payload": {}}
    )

    assert response.status_code == 422
    assert "conteúdo do arquivo .avsc" in response.text


def test_validate_payload_route_never_touches_kafka(api_client, monkeypatch):
    build_producer_calls = []
    build_admin_client_calls = []
    monkeypatch.setattr(
        kafka_service.kafka_connection,
        "build_producer",
        lambda configuration: build_producer_calls.append(configuration),
    )
    monkeypatch.setattr(
        kafka_service.kafka_connection,
        "build_admin_client",
        lambda configuration: build_admin_client_calls.append(configuration),
    )

    api_client.post(
        "/api/v1/messages/validate",
        json={"avsc_content": SIMPLE_AVSC, "payload": {"id": 1, "valor": 10.5}},
    )

    assert build_producer_calls == []
    assert build_admin_client_calls == []


def test_messages_route_is_documented_in_openapi_schema(api_client):
    response = api_client.get("/openapi.json")

    paths = response.json()["paths"]
    assert "post" in paths["/api/v1/messages/validate"]


# --- POST /api/v1/messages (US-003b/US-004a, TASK-035/TASK-038): mesmo
# services/kafka_service.py usado pela UI, comparável ao resultado obtido
# pela tela (SC-005) ---


def test_publish_route_returns_success_with_partition_and_offset(api_client, monkeypatch):
    # cenário 1 do Acceptance Scenario de US-004a
    _create_configuration()
    kafka_service.save_schema(SIMPLE_AVSC)
    monkeypatch.setattr(
        kafka_service.kafka_connection, "build_producer", lambda configuration: _FakeProducer()
    )

    response = api_client.post(
        "/api/v1/messages",
        json={
            "configuration": "Desenvolvimento",
            "topic": "pedido-criado",
            "schema": "Pedido",
            "payload": {"id": 1, "valor": 10.5},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["topic"] == "pedido-criado"
    assert body["partition"] == 2
    assert body["offset"] == 12345


def test_publish_route_rejects_an_incompatible_payload_without_touching_kafka(api_client):
    # cenário 2 do Acceptance Scenario de US-004a
    _create_configuration()
    kafka_service.save_schema(SIMPLE_AVSC)

    response = api_client.post(
        "/api/v1/messages",
        json={
            "configuration": "Desenvolvimento",
            "topic": "pedido-criado",
            "schema": "Pedido",
            "payload": {"id": 1, "valor": "nao-e-numero"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]


def test_publish_route_returns_404_for_a_nonexistent_configuration(api_client):
    # cenário 3 do Acceptance Scenario de US-004a
    kafka_service.save_schema(SIMPLE_AVSC)

    response = api_client.post(
        "/api/v1/messages",
        json={
            "configuration": "Inexistente",
            "topic": "pedido-criado",
            "schema": "Pedido",
            "payload": {"id": 1, "valor": 10.5},
        },
    )

    assert response.status_code == 404
    assert "Inexistente" in response.json()["detail"]


def test_publish_route_returns_404_for_a_nonexistent_schema(api_client):
    # cenário 3 do Acceptance Scenario de US-004a
    _create_configuration()

    response = api_client.post(
        "/api/v1/messages",
        json={
            "configuration": "Desenvolvimento",
            "topic": "pedido-criado",
            "schema": "Inexistente",
            "payload": {"id": 1, "valor": 10.5},
        },
    )

    assert response.status_code == 404
    assert "Inexistente" in response.json()["detail"]


def test_publish_route_is_documented_in_openapi_schema(api_client):
    response = api_client.get("/openapi.json")

    paths = response.json()["paths"]
    assert "post" in paths["/api/v1/messages"]
