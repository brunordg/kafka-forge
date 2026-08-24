import pytest
from pydantic import ValidationError

from app.api.schemas.configurations import (
    ConfigurationCreateRequest,
    ConfigurationResponse,
    KafkaConfigPayload,
    SchemaRegistryConfigPayload,
)
from app.config.models import EnvironmentConfiguration, KafkaConfig, SecurityProtocol


def _full_request_payload() -> dict:
    return {
        "nome": "Desenvolvimento",
        "kafka": {
            "bootstrap_servers": "localhost:9092",
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "PLAIN",
            "username": "dev",
            "password": "dev-secret",
            "ca_cert": "-----BEGIN CERTIFICATE-----...",
            "client_cert": "-----BEGIN CERTIFICATE-----...",
            "client_key": "-----BEGIN PRIVATE KEY-----...",
            "client_key_password": "chave-secreta",
        },
        "schema_registry": {
            "url": "https://schema-registry.dev.local:8081",
            "username": "dev",
            "password": "dev-secret",
        },
    }


# --- cobertura de todos os campos da Configuração de Ambiente (DoD 1) ---


def test_kafka_payload_covers_every_kafka_config_field():
    assert set(KafkaConfigPayload.model_fields) == set(KafkaConfig.model_fields)


def test_schema_registry_payload_covers_every_schema_registry_config_field():
    assert set(SchemaRegistryConfigPayload.model_fields) == {
        "url",
        "username",
        "password",
        "ca_cert",
        "client_cert",
        "client_key",
    }


def test_create_request_covers_every_environment_configuration_field():
    assert set(ConfigurationCreateRequest.model_fields) == set(
        EnvironmentConfiguration.model_fields
    )


def test_response_covers_every_environment_configuration_field():
    assert set(ConfigurationResponse.model_fields) == set(EnvironmentConfiguration.model_fields)


# --- request válido, com e sem schema_registry ---


def test_create_request_accepts_full_payload():
    request = ConfigurationCreateRequest.model_validate(_full_request_payload())

    assert request.nome == "Desenvolvimento"
    assert request.kafka.bootstrap_servers == "localhost:9092"
    assert request.schema_registry.url == "https://schema-registry.dev.local:8081"


def test_create_request_accepts_payload_without_schema_registry():
    payload = _full_request_payload()
    del payload["schema_registry"]

    request = ConfigurationCreateRequest.model_validate(payload)

    assert request.schema_registry is None


# --- conversão de/para o modelo de domínio (usada pela TASK-013) ---


def test_to_domain_produces_an_equivalent_environment_configuration():
    request = ConfigurationCreateRequest.model_validate(_full_request_payload())

    domain = request.to_domain()

    assert isinstance(domain, EnvironmentConfiguration)
    assert domain.nome == "Desenvolvimento"
    assert domain.kafka.security_protocol is SecurityProtocol.SASL_SSL
    assert domain.schema_registry.url == "https://schema-registry.dev.local:8081"


def test_response_from_domain_round_trips_correctly():
    domain = EnvironmentConfiguration.model_validate(_full_request_payload())

    response = ConfigurationResponse.from_domain(domain)

    assert response.nome == domain.nome
    assert response.kafka.bootstrap_servers == domain.kafka.bootstrap_servers
    assert response.schema_registry.url == domain.schema_registry.url


def test_response_from_domain_without_schema_registry():
    payload = _full_request_payload()
    del payload["schema_registry"]
    domain = EnvironmentConfiguration.model_validate(payload)

    response = ConfigurationResponse.from_domain(domain)

    assert response.schema_registry is None


# --- mensagens de erro compreensíveis (DoD 3) ---


def test_empty_nome_raises_understandable_message():
    payload = _full_request_payload()
    payload["nome"] = "   "

    with pytest.raises(ValidationError) as exc_info:
        ConfigurationCreateRequest.model_validate(payload)

    assert "nome da configuração não pode ficar vazio" in str(exc_info.value)


def test_empty_bootstrap_servers_raises_understandable_message():
    payload = _full_request_payload()
    payload["kafka"]["bootstrap_servers"] = "   "

    with pytest.raises(ValidationError) as exc_info:
        ConfigurationCreateRequest.model_validate(payload)

    assert "endereço de broker Kafka" in str(exc_info.value)


def test_empty_schema_registry_url_raises_understandable_message():
    payload = _full_request_payload()
    payload["schema_registry"]["url"] = "   "

    with pytest.raises(ValidationError) as exc_info:
        ConfigurationCreateRequest.model_validate(payload)

    assert "URL do Schema Registry" in str(exc_info.value)


def test_invalid_security_protocol_message_lists_the_accepted_values():
    payload = _full_request_payload()
    payload["kafka"]["security_protocol"] = "TCP"

    with pytest.raises(ValidationError) as exc_info:
        ConfigurationCreateRequest.model_validate(payload)

    message = str(exc_info.value)
    assert "security_protocol" in message
    assert "PLAINTEXT" in message


def test_missing_bootstrap_servers_is_reported_with_the_field_path():
    payload = _full_request_payload()
    del payload["kafka"]["bootstrap_servers"]

    with pytest.raises(ValidationError) as exc_info:
        ConfigurationCreateRequest.model_validate(payload)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("kafka", "bootstrap_servers") for error in errors)
