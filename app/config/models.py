from enum import Enum

from pydantic import BaseModel, Field


class SecurityProtocol(str, Enum):
    PLAINTEXT = "PLAINTEXT"
    SSL = "SSL"
    SASL_PLAINTEXT = "SASL_PLAINTEXT"
    SASL_SSL = "SASL_SSL"


class SaslMechanism(str, Enum):
    """Decisão Q5 (seção 7 do plano): apenas PLAIN suportado nesta etapa."""

    PLAIN = "PLAIN"


class KafkaConfig(BaseModel):
    bootstrap_servers: str = Field(min_length=1)
    security_protocol: SecurityProtocol
    sasl_mechanism: SaslMechanism | None = None
    username: str | None = None
    password: str | None = None
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None
    client_key_password: str | None = None


class SchemaRegistryConfig(BaseModel):
    url: str = Field(min_length=1)
    username: str | None = None
    password: str | None = None
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None


class EnvironmentConfiguration(BaseModel):
    nome: str = Field(min_length=1)
    kafka: KafkaConfig
    schema_registry: SchemaRegistryConfig | None = None
