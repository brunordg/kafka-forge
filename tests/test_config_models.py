import pytest
from pydantic import ValidationError

from app.config.models import (
    EnvironmentConfiguration,
    KafkaConfig,
    SaslMechanism,
    SchemaRegistryConfig,
    SecurityProtocol,
)


def test_environment_configuration_valid_with_schema_registry():
    config = EnvironmentConfiguration(
        nome="Desenvolvimento",
        kafka=KafkaConfig(
            bootstrap_servers="localhost:9092",
            security_protocol=SecurityProtocol.SASL_SSL,
            sasl_mechanism=SaslMechanism.PLAIN,
            username="dev",
            password="dev-secret",
            ca_cert="-----BEGIN CERTIFICATE-----...",
            client_cert="-----BEGIN CERTIFICATE-----...",
            client_key="-----BEGIN PRIVATE KEY-----...",
            client_key_password="chave-secreta",
        ),
        schema_registry=SchemaRegistryConfig(
            url="https://schema-registry.dev.local:8081",
            username="dev",
            password="dev-secret",
        ),
    )

    assert config.nome == "Desenvolvimento"
    assert config.kafka.security_protocol is SecurityProtocol.SASL_SSL
    assert config.schema_registry.url == "https://schema-registry.dev.local:8081"


def test_environment_configuration_valid_without_schema_registry():
    config = EnvironmentConfiguration(
        nome="Homologação",
        kafka=KafkaConfig(
            bootstrap_servers="broker1:9092,broker2:9092",
            security_protocol=SecurityProtocol.PLAINTEXT,
        ),
    )

    assert config.schema_registry is None


def test_kafka_config_accepts_only_bootstrap_servers_and_security_protocol():
    kafka = KafkaConfig(
        bootstrap_servers="localhost:9092",
        security_protocol=SecurityProtocol.PLAINTEXT,
    )

    assert kafka.sasl_mechanism is None
    assert kafka.username is None
    assert kafka.password is None
    assert kafka.ca_cert is None
    assert kafka.client_cert is None
    assert kafka.client_key is None
    assert kafka.client_key_password is None


def test_client_key_password_can_be_omitted_even_with_client_key_set():
    # Decisão explícita da seção 5 do plano: client_key_password é opcional
    # mesmo quando client_key exige senha; essa checagem só acontece no
    # teste de conexão (US-001b, cenário 3), não na validação do modelo.
    kafka = KafkaConfig(
        bootstrap_servers="localhost:9092",
        security_protocol=SecurityProtocol.SSL,
        client_cert="cert",
        client_key="chave-protegida-por-senha",
    )

    assert kafka.client_key == "chave-protegida-por-senha"
    assert kafka.client_key_password is None


def test_missing_bootstrap_servers_is_rejected():
    with pytest.raises(ValidationError):
        KafkaConfig(security_protocol=SecurityProtocol.PLAINTEXT)


def test_empty_bootstrap_servers_is_rejected():
    with pytest.raises(ValidationError):
        KafkaConfig(bootstrap_servers="", security_protocol=SecurityProtocol.PLAINTEXT)


def test_invalid_security_protocol_is_rejected():
    with pytest.raises(ValidationError):
        KafkaConfig(bootstrap_servers="localhost:9092", security_protocol="TCP")


def test_invalid_sasl_mechanism_is_rejected():
    with pytest.raises(ValidationError):
        KafkaConfig(
            bootstrap_servers="localhost:9092",
            security_protocol=SecurityProtocol.SASL_SSL,
            sasl_mechanism="SCRAM-SHA-256",
        )


def test_missing_nome_is_rejected():
    with pytest.raises(ValidationError):
        EnvironmentConfiguration(
            kafka=KafkaConfig(
                bootstrap_servers="localhost:9092",
                security_protocol=SecurityProtocol.PLAINTEXT,
            )
        )


def test_empty_nome_is_rejected():
    with pytest.raises(ValidationError):
        EnvironmentConfiguration(
            nome="",
            kafka=KafkaConfig(
                bootstrap_servers="localhost:9092",
                security_protocol=SecurityProtocol.PLAINTEXT,
            ),
        )


def test_missing_schema_registry_url_is_rejected():
    with pytest.raises(ValidationError):
        SchemaRegistryConfig(username="dev")
