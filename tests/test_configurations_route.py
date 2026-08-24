from confluent_kafka import KafkaError, KafkaException

from app.services import kafka_service


def _payload(nome: str, bootstrap_servers: str = "localhost:9092") -> dict:
    return {
        "nome": nome,
        "kafka": {
            "bootstrap_servers": bootstrap_servers,
            "security_protocol": "PLAINTEXT",
        },
    }


class _FakeAdminClient:
    """Dublê de `AdminClient`: nunca abre um socket de verdade, então os
    testes de `POST /configurations/{name}/test` ficam rápidos e
    determinísticos sem depender de um Kafka real (plano, seção 12)."""

    def __init__(self, *, error: KafkaException | None = None):
        self._error = error

    def list_topics(self, timeout=None):
        if self._error is not None:
            raise self._error
        return object()


def _patch_admin_client(monkeypatch, admin_client: _FakeAdminClient) -> None:
    monkeypatch.setattr(
        kafka_service.kafka_connection, "build_admin_client", lambda configuration: admin_client
    )


def test_list_configurations_starts_empty(api_client):
    response = api_client.get("/api/v1/configurations")

    assert response.status_code == 200
    assert response.json() == []


def test_create_configuration_returns_201_with_the_created_configuration(api_client):
    response = api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento"))

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Desenvolvimento"
    assert body["kafka"]["bootstrap_servers"] == "localhost:9092"
    assert body["kafka"]["security_protocol"] == "PLAINTEXT"


def test_created_configuration_can_be_reopened_via_subsequent_get(api_client):
    # cenário 1 de US-001a
    api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento"))

    response = api_client.get("/api/v1/configurations")

    assert response.status_code == 200
    [configuration] = response.json()
    assert configuration["nome"] == "Desenvolvimento"
    assert configuration["kafka"]["bootstrap_servers"] == "localhost:9092"


def test_creating_a_duplicate_name_is_rejected_without_overwriting(api_client):
    api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento", "original:9092"))

    response = api_client.post(
        "/api/v1/configurations", json=_payload("Desenvolvimento", "outro:9092")
    )

    assert response.status_code == 409
    assert "Desenvolvimento" in response.json()["detail"]

    listed = api_client.get("/api/v1/configurations").json()
    assert len(listed) == 1
    assert listed[0]["kafka"]["bootstrap_servers"] == "original:9092"


def test_create_with_empty_nome_returns_422_with_an_understandable_message(api_client):
    response = api_client.post("/api/v1/configurations", json=_payload("   "))

    assert response.status_code == 422
    assert "nome da configuração não pode ficar vazio" in response.text


def test_create_with_empty_bootstrap_servers_returns_422_with_an_understandable_message(api_client):
    response = api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento", "   "))

    assert response.status_code == 422
    assert "endereço de broker Kafka" in response.text


def test_configurations_route_is_documented_in_openapi_schema(api_client):
    response = api_client.get("/openapi.json")

    paths = response.json()["paths"]
    assert "get" in paths["/api/v1/configurations"]
    assert "post" in paths["/api/v1/configurations"]
    assert "delete" in paths["/api/v1/configurations/{name}"]
    assert "post" in paths["/api/v1/configurations/{name}/test"]


def test_delete_configuration_removes_it_from_a_subsequent_get(api_client):
    api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento"))

    response = api_client.delete("/api/v1/configurations/Desenvolvimento")

    assert response.status_code == 204
    assert api_client.get("/api/v1/configurations").json() == []


def test_delete_configuration_does_not_affect_the_others(api_client):
    api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento"))
    api_client.post("/api/v1/configurations", json=_payload("Homologacao", "homolog:9092"))

    api_client.delete("/api/v1/configurations/Desenvolvimento")

    listed = api_client.get("/api/v1/configurations").json()
    assert [c["nome"] for c in listed] == ["Homologacao"]


def test_delete_nonexistent_configuration_returns_404_with_an_understandable_message(api_client):
    response = api_client.delete("/api/v1/configurations/Inexistente")

    assert response.status_code == 404
    assert "Inexistente" in response.json()["detail"]


def test_test_configuration_route_returns_success_for_a_reachable_broker(api_client, monkeypatch):
    api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento"))
    _patch_admin_client(monkeypatch, _FakeAdminClient())

    response = api_client.post("/api/v1/configurations/Desenvolvimento/test")

    assert response.status_code == 200
    body = response.json()
    assert body["kafka"]["success"] is True
    assert "sucesso" in body["kafka"]["message"].lower()
    assert body["schema_registry"] is None


def test_test_configuration_route_returns_understandable_failure_for_unreachable_broker(
    api_client, monkeypatch
):
    # cenário 2 de US-001b: broker inexistente
    api_client.post("/api/v1/configurations", json=_payload("Desenvolvimento"))
    error = KafkaException(KafkaError(KafkaError._TRANSPORT, "Simulação: broker inacessível"))
    _patch_admin_client(monkeypatch, _FakeAdminClient(error=error))

    response = api_client.post("/api/v1/configurations/Desenvolvimento/test")

    assert response.status_code == 200
    body = response.json()
    assert body["kafka"]["success"] is False
    assert "Simulação: broker inacessível" in body["kafka"]["message"]


def test_test_configuration_route_for_nonexistent_configuration_returns_404(api_client):
    response = api_client.post("/api/v1/configurations/Inexistente/test")

    assert response.status_code == 404
    assert "Inexistente" in response.json()["detail"]
