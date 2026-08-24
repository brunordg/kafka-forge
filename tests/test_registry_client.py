from pathlib import Path

import pytest

from app.config.models import SchemaRegistryConfig
from app.exceptions import SchemaRegistryError
from app.registry import client as registry_client


class _FakeRegisteredSchema:
    def __init__(self, schema_str: str):
        class _Schema:
            def __init__(self, schema_str: str):
                self.schema_str = schema_str

        self.schema = _Schema(schema_str)


class _FakeSchemaRegistryClient:
    """Dublê do `SchemaRegistryClient` da Confluent: nunca abre um socket
    real, então os testes de `registry/client.py` ficam rápidos e
    determinísticos sem depender de um Schema Registry real (plano, seção
    12)."""

    last_conf: dict | None = None

    def __init__(self, conf: dict):
        _FakeSchemaRegistryClient.last_conf = conf
        self._conf = conf

    def get_subjects(self):
        return ["Pedido"]

    def get_versions(self, subject_name):
        return [1, 2]

    def get_version(self, subject_name, version="latest"):
        return _FakeRegisteredSchema('{"type": "record", "name": "Pedido", "fields": []}')

    def register_schema(self, subject_name, schema):
        return 42


class _FailingSchemaRegistryClient:
    def __init__(self, conf: dict):
        pass

    def get_subjects(self):
        raise ConnectionError("Simulação: Schema Registry inacessível")


def _config(**kwargs) -> SchemaRegistryConfig:
    return SchemaRegistryConfig(url="https://schema-registry.local", **kwargs)


def test_test_connection_succeeds_for_an_accessible_registry(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FakeSchemaRegistryClient)

    registry_client.test_connection(_config())  # não deve levantar


def test_test_connection_raises_a_schema_registry_error_for_a_failure(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FailingSchemaRegistryClient)

    with pytest.raises(SchemaRegistryError) as exc_info:
        registry_client.test_connection(_config())

    assert "Simulação: Schema Registry inacessível" in exc_info.value.technical_detail


def test_list_subjects_returns_the_subjects_from_the_registry(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FakeSchemaRegistryClient)

    assert registry_client.list_subjects(_config()) == ["Pedido"]


def test_list_versions_returns_the_versions_for_a_subject(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FakeSchemaRegistryClient)

    assert registry_client.list_versions(_config(), "Pedido") == [1, 2]


def test_get_schema_returns_the_avsc_content(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FakeSchemaRegistryClient)

    content = registry_client.get_schema(_config(), "Pedido")

    assert '"name": "Pedido"' in content


def test_register_or_reuse_schema_returns_the_schema_id(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FakeSchemaRegistryClient)

    schema_id = registry_client.register_or_reuse_schema(
        _config(), "Pedido", '{"type": "record", "name": "Pedido", "fields": []}'
    )

    assert schema_id == 42


def test_basic_auth_is_configured_from_username_and_password(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FakeSchemaRegistryClient)

    registry_client.test_connection(_config(username="dev", password="senha"))

    assert _FakeSchemaRegistryClient.last_conf["basic.auth.user.info"] == "dev:senha"


def test_certificates_are_written_to_temp_files_and_removed_after_use(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FakeSchemaRegistryClient)

    registry_client.test_connection(
        _config(ca_cert="ca-content", client_cert="cert-content", client_key="key-content")
    )

    conf = _FakeSchemaRegistryClient.last_conf
    ca_path = Path(conf["ssl.ca.location"])
    cert_path = Path(conf["ssl.certificate.location"])
    key_path = Path(conf["ssl.key.location"])

    # os arquivos temporários são removidos pelo `_client` logo após o uso
    assert not ca_path.exists()
    assert not cert_path.exists()
    assert not key_path.exists()


def test_get_schema_raises_a_schema_registry_error_for_a_failure(monkeypatch):
    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _FailingSchemaRegistryClient)

    class _AlwaysFailing(_FailingSchemaRegistryClient):
        def get_version(self, subject_name, version="latest"):
            raise ConnectionError("Simulação: subject inexistente")

    monkeypatch.setattr(registry_client, "SchemaRegistryClient", _AlwaysFailing)

    with pytest.raises(SchemaRegistryError):
        registry_client.get_schema(_config(), "Inexistente")
