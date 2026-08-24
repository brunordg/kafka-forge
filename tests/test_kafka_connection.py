import pytest
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient

from app.config.models import EnvironmentConfiguration, KafkaConfig, SaslMechanism, SecurityProtocol
from app.exceptions import KafkaAuthenticationError
from app.kafka.connection import (
    CONNECTION_TIMEOUT_MS,
    build_admin_client,
    build_client_config,
    build_producer,
)

UNENCRYPTED_KEY = "-----BEGIN PRIVATE KEY-----\nconteudo\n-----END PRIVATE KEY-----"
PKCS8_ENCRYPTED_KEY = "-----BEGIN ENCRYPTED PRIVATE KEY-----\nconteudo\n-----END ENCRYPTED PRIVATE KEY-----"
PKCS1_ENCRYPTED_KEY = (
    "-----BEGIN RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\nDEK-Info: AES-128-CBC,0\n\n"
    "conteudo\n-----END RSA PRIVATE KEY-----"
)


def _configuration(**kafka_kwargs) -> EnvironmentConfiguration:
    kafka_kwargs.setdefault("bootstrap_servers", "localhost:9092")
    kafka_kwargs.setdefault("security_protocol", SecurityProtocol.PLAINTEXT)
    return EnvironmentConfiguration(nome="Desenvolvimento", kafka=KafkaConfig(**kafka_kwargs))


# --- timeout único e reutilizável (DoD 2) ---


def test_connection_timeout_is_ten_seconds():
    assert CONNECTION_TIMEOUT_MS == 10_000


def test_timeout_constant_is_applied_to_socket_and_handshake_settings():
    config = build_client_config(_configuration())

    assert config["socket.timeout.ms"] == CONNECTION_TIMEOUT_MS
    assert config["socket.connection.setup.timeout.ms"] == CONNECTION_TIMEOUT_MS


# --- combinações de security_protocol (DoD 1) ---


def test_plaintext_config_has_no_sasl_or_ssl_properties():
    config = build_client_config(_configuration(security_protocol=SecurityProtocol.PLAINTEXT))

    assert config["security.protocol"] == "PLAINTEXT"
    assert not any(key.startswith("sasl.") for key in config)
    assert not any(key.startswith("ssl.") for key in config)


def test_ssl_config_includes_certificate_properties():
    config = build_client_config(
        _configuration(
            security_protocol=SecurityProtocol.SSL,
            ca_cert="ca-content",
            client_cert="cert-content",
            client_key=UNENCRYPTED_KEY,
        )
    )

    assert config["security.protocol"] == "SSL"
    assert config["ssl.ca.pem"] == "ca-content"
    assert config["ssl.certificate.pem"] == "cert-content"
    assert config["ssl.key.pem"] == UNENCRYPTED_KEY
    assert not any(key.startswith("sasl.") for key in config)


def test_sasl_plaintext_config_includes_credentials():
    config = build_client_config(
        _configuration(
            security_protocol=SecurityProtocol.SASL_PLAINTEXT,
            sasl_mechanism=SaslMechanism.PLAIN,
            username="dev",
            password="dev-secret",
        )
    )

    assert config["security.protocol"] == "SASL_PLAINTEXT"
    assert config["sasl.mechanisms"] == "PLAIN"
    assert config["sasl.username"] == "dev"
    assert config["sasl.password"] == "dev-secret"
    assert not any(key.startswith("ssl.") for key in config)


def test_sasl_ssl_config_combines_credentials_and_certificates():
    config = build_client_config(
        _configuration(
            security_protocol=SecurityProtocol.SASL_SSL,
            username="dev",
            password="dev-secret",
            ca_cert="ca-content",
        )
    )

    assert config["security.protocol"] == "SASL_SSL"
    assert config["sasl.username"] == "dev"
    assert config["ssl.ca.pem"] == "ca-content"


def test_sasl_mechanism_defaults_to_plain_when_not_set():
    config = build_client_config(
        _configuration(security_protocol=SecurityProtocol.SASL_PLAINTEXT)
    )

    assert config["sasl.mechanisms"] == "PLAIN"


# --- certificado sem senha de chave privada quando a chave exige (DoD 3) ---


def test_encrypted_pkcs8_key_without_password_is_rejected_before_ssl_config():
    configuration = _configuration(
        security_protocol=SecurityProtocol.SSL,
        client_cert="cert-content",
        client_key=PKCS8_ENCRYPTED_KEY,
    )

    with pytest.raises(KafkaAuthenticationError) as exc_info:
        build_client_config(configuration)

    assert "client_key_password" in exc_info.value.friendly_message
    assert exc_info.value.technical_detail


def test_encrypted_pkcs1_key_without_password_is_rejected():
    configuration = _configuration(
        security_protocol=SecurityProtocol.SASL_SSL,
        client_key=PKCS1_ENCRYPTED_KEY,
    )

    with pytest.raises(KafkaAuthenticationError):
        build_client_config(configuration)


def test_encrypted_key_with_password_is_accepted():
    config = build_client_config(
        _configuration(
            security_protocol=SecurityProtocol.SSL,
            client_key=PKCS8_ENCRYPTED_KEY,
            client_key_password="senha-correta",
        )
    )

    assert config["ssl.key.pem"] == PKCS8_ENCRYPTED_KEY
    assert config["ssl.key.password"] == "senha-correta"


def test_unencrypted_key_without_password_is_accepted():
    config = build_client_config(
        _configuration(security_protocol=SecurityProtocol.SSL, client_key=UNENCRYPTED_KEY)
    )

    assert config["ssl.key.pem"] == UNENCRYPTED_KEY
    assert "ssl.key.password" not in config


def test_client_key_check_is_skipped_for_non_ssl_protocols():
    # client_key preenchido "por engano" numa configuração PLAINTEXT não
    # deve nunca ser usado (nem checado) — fiel à decisão da TASK-007 de
    # não validar client_key/client_key_password de forma cruzada no
    # modelo de domínio.
    config = build_client_config(
        _configuration(security_protocol=SecurityProtocol.PLAINTEXT, client_key=PKCS8_ENCRYPTED_KEY)
    )

    assert "ssl.key.pem" not in config


# --- constrói clientes librdkafka reais e válidos (DoD 1, sem precisar de broker) ---


@pytest.mark.parametrize(
    "security_protocol",
    [
        SecurityProtocol.PLAINTEXT,
        SecurityProtocol.SSL,
        SecurityProtocol.SASL_PLAINTEXT,
        SecurityProtocol.SASL_SSL,
    ],
)
def test_build_producer_constructs_a_valid_client_for_every_security_protocol(security_protocol):
    configuration = _configuration(
        security_protocol=security_protocol,
        username="dev",
        password="dev-secret",
    )

    producer = build_producer(configuration)

    assert isinstance(producer, Producer)


@pytest.mark.parametrize(
    "security_protocol",
    [
        SecurityProtocol.PLAINTEXT,
        SecurityProtocol.SSL,
        SecurityProtocol.SASL_PLAINTEXT,
        SecurityProtocol.SASL_SSL,
    ],
)
def test_build_admin_client_constructs_a_valid_client_for_every_security_protocol(
    security_protocol,
):
    configuration = _configuration(
        security_protocol=security_protocol,
        username="dev",
        password="dev-secret",
    )

    admin_client = build_admin_client(configuration)

    assert isinstance(admin_client, AdminClient)
