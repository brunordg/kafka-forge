from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.kafka_service import PayloadValidationResult, PublishResult


class PayloadValidateRequest(BaseModel):
    avsc_content: str
    payload: dict

    @field_validator("avsc_content")
    @classmethod
    def _avsc_content_obrigatorio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Informe o conteúdo do arquivo .avsc.")
        return value


class PayloadProblemResponse(BaseModel):
    campo: str
    tipo_esperado: str
    tipo_recebido: str


class PayloadValidationResponse(BaseModel):
    valid: bool
    message: str
    problems: list[PayloadProblemResponse]

    @classmethod
    def from_domain(cls, result: PayloadValidationResult) -> "PayloadValidationResponse":
        return cls(valid=result.valid, message=result.message, problems=result.problems)


class MessagePublishRequest(BaseModel):
    """Contrato de `POST /api/v1/messages` (briefing, seção API REST; plano
    §6.1): `schema` referencia, por nome, um schema já carregado via
    `POST /api/v1/schema/validate`+persistência (TASK-034b) ou pela tela
    Schemas Avro — não o conteúdo `.avsc` bruto. Campo Python `schema_`
    com alias `schema` pelo mesmo motivo de `services/operation_log.py`:
    evita colidir com atributos de `BaseModel`. `schema` é opcional: o
    schema Avro serve para validar o payload, não é um requisito para
    publicar — sem ele, o payload é publicado como JSON puro."""

    model_config = ConfigDict(populate_by_name=True)

    configuration: str
    topic: str
    schema_: str | None = Field(default=None, alias="schema")
    key: str | None = None
    payload: dict

    @field_validator("configuration")
    @classmethod
    def _configuration_obrigatoria(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Informe o nome da configuração de ambiente.")
        return value

    @field_validator("topic")
    @classmethod
    def _topic_obrigatorio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Informe o tópico Kafka de destino.")
        return value

    @field_validator("schema_")
    @classmethod
    def _schema_em_branco_vira_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value


class MessagePublishResponse(BaseModel):
    """Formato de resposta do contrato acima: sucesso traz `topic`/
    `partition`/`offset`; falha traz `error` — exatamente as duas formas
    documentadas no briefing (seção API REST)."""

    success: bool
    topic: str | None = None
    partition: int | None = None
    offset: int | None = None
    error: str | None = None

    @classmethod
    def from_domain(cls, result: PublishResult) -> "MessagePublishResponse":
        if result.success:
            return cls(success=True, topic=result.topic, partition=result.partition, offset=result.offset)
        return cls(success=False, error=result.message)
