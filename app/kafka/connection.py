from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient

from app.config.models import EnvironmentConfiguration, KafkaConfig, SaslMechanism, SecurityProtocol
from app.exceptions import KafkaAuthenticationError

# Decisão Q2 (seção 7 do plano): 10 segundos para testar conexão, testar
# Schema Registry e publicar. Única constante reutilizada tanto no
# handshake TCP/SSL/SASL (`socket.connection.setup.timeout.ms`) quanto nas
# operações subsequentes sobre o socket já conectado (`socket.timeout.ms`).
CONNECTION_TIMEOUT_MS = 10_000

_SASL_PROTOCOLS = {SecurityProtocol.SASL_PLAINTEXT, SecurityProtocol.SASL_SSL}
_SSL_PROTOCOLS = {SecurityProtocol.SSL, SecurityProtocol.SASL_SSL}

# Cabeçalhos PEM padrão que indicam uma chave privada criptografada por
# senha, tanto no formato PKCS#8 (`ENCRYPTED PRIVATE KEY`) quanto no
# formato tradicional PKCS#1 (`Proc-Type: 4,ENCRYPTED`). Checagem só de
# texto, sem depender de nenhuma biblioteca de criptografia — suficiente
# para detectar o problema antes de qualquer tentativa de handshake TLS.
_ENCRYPTED_PRIVATE_KEY_MARKERS = (
    "-----BEGIN ENCRYPTED PRIVATE KEY-----",
    "Proc-Type: 4,ENCRYPTED",
)


def _client_key_requires_password(client_key: str) -> bool:
    return any(marker in client_key for marker in _ENCRYPTED_PRIVATE_KEY_MARKERS)


def _ensure_client_key_password_present_when_required(kafka: KafkaConfig) -> None:
    if not kafka.client_key or kafka.client_key_password:
        return
    if _client_key_requires_password(kafka.client_key):
        raise KafkaAuthenticationError.missing_client_key_password(
            "PEM de client_key contém um cabeçalho de chave criptografada "
            "(ENCRYPTED PRIVATE KEY ou Proc-Type: 4,ENCRYPTED) e "
            "client_key_password está vazio."
        )


def build_client_config(configuration: EnvironmentConfiguration) -> dict:
    """Monta o dicionário de configuração `librdkafka` a partir de uma
    Configuração de Ambiente, suportando qualquer combinação de
    `security_protocol` (PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL)."""
    kafka = configuration.kafka

    config: dict = {
        "bootstrap.servers": kafka.bootstrap_servers,
        "security.protocol": kafka.security_protocol.value,
        "socket.timeout.ms": CONNECTION_TIMEOUT_MS,
        "socket.connection.setup.timeout.ms": CONNECTION_TIMEOUT_MS,
    }

    if kafka.security_protocol in _SASL_PROTOCOLS:
        config["sasl.mechanisms"] = (kafka.sasl_mechanism or SaslMechanism.PLAIN).value
        if kafka.username is not None:
            config["sasl.username"] = kafka.username
        if kafka.password is not None:
            config["sasl.password"] = kafka.password

    if kafka.security_protocol in _SSL_PROTOCOLS:
        _ensure_client_key_password_present_when_required(kafka)
        if kafka.ca_cert is not None:
            config["ssl.ca.pem"] = kafka.ca_cert
        if kafka.client_cert is not None:
            config["ssl.certificate.pem"] = kafka.client_cert
        if kafka.client_key is not None:
            config["ssl.key.pem"] = kafka.client_key
        if kafka.client_key_password is not None:
            config["ssl.key.password"] = kafka.client_key_password

    return config


def build_producer(configuration: EnvironmentConfiguration) -> Producer:
    return Producer(build_client_config(configuration))


def build_admin_client(configuration: EnvironmentConfiguration) -> AdminClient:
    return AdminClient(build_client_config(configuration))
