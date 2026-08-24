from pydantic import BaseModel, field_validator

from app.config.models import (
    EnvironmentConfiguration,
    KafkaConfig,
    SaslMechanism,
    SchemaRegistryConfig,
    SecurityProtocol,
)
from app.services.kafka_service import ConfigurationTestResult, ConnectionTestResult


class KafkaConfigPayload(BaseModel):
    bootstrap_servers: str
    security_protocol: SecurityProtocol
    sasl_mechanism: SaslMechanism | None = None
    username: str | None = None
    password: str | None = None
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None
    client_key_password: str | None = None

    @field_validator("bootstrap_servers")
    @classmethod
    def _bootstrap_servers_obrigatorio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "Informe ao menos um endereço de broker Kafka em bootstrap_servers."
            )
        return value


class SchemaRegistryConfigPayload(BaseModel):
    url: str
    username: str | None = None
    password: str | None = None
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None

    @field_validator("url")
    @classmethod
    def _url_obrigatoria(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Informe a URL do Schema Registry.")
        return value


class ConfigurationCreateRequest(BaseModel):
    nome: str
    kafka: KafkaConfigPayload
    schema_registry: SchemaRegistryConfigPayload | None = None

    @field_validator("nome")
    @classmethod
    def _nome_obrigatorio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O nome da configuração não pode ficar vazio.")
        return value

    def to_domain(self) -> EnvironmentConfiguration:
        return EnvironmentConfiguration.model_validate(self.model_dump())


class ConfigurationResponse(BaseModel):
    nome: str
    kafka: KafkaConfigPayload
    schema_registry: SchemaRegistryConfigPayload | None = None

    @classmethod
    def from_domain(cls, configuration: EnvironmentConfiguration) -> "ConfigurationResponse":
        return cls.model_validate(configuration.model_dump())


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    technical_detail: str = ""

    @classmethod
    def from_domain(cls, result: ConnectionTestResult) -> "ConnectionTestResponse":
        return cls(
            success=result.success,
            message=result.message,
            technical_detail=result.technical_detail,
        )


class ConfigurationTestResponse(BaseModel):
    """Resultado de `POST /api/v1/configurations/{name}/test` (TASK-046):
    Kafka e Schema Registry separados e identificáveis — `schema_registry`
    fica `None` quando o ambiente não tem Schema Registry configurado
    (FR-007), em vez de reportar uma falha por algo que não existe."""

    kafka: ConnectionTestResponse
    schema_registry: ConnectionTestResponse | None = None

    @classmethod
    def from_domain(cls, result: ConfigurationTestResult) -> "ConfigurationTestResponse":
        return cls(
            kafka=ConnectionTestResponse.from_domain(result.kafka),
            schema_registry=(
                ConnectionTestResponse.from_domain(result.schema_registry)
                if result.schema_registry is not None
                else None
            ),
        )


# Confere, na importação do módulo, que nenhum campo da Configuração de
# Ambiente (seção 5 do plano) ficou de fora dos contratos HTTP acima — se
# `config/models.py` ganhar um campo novo sem o correspondente aqui, a
# aplicação falha ao subir em vez de silenciosamente omitir o campo da API.
assert set(KafkaConfigPayload.model_fields) == set(KafkaConfig.model_fields)
assert set(SchemaRegistryConfigPayload.model_fields) == set(SchemaRegistryConfig.model_fields)
assert set(ConfigurationCreateRequest.model_fields) == set(EnvironmentConfiguration.model_fields)
assert set(ConfigurationResponse.model_fields) == set(EnvironmentConfiguration.model_fields)
