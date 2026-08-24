from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.operation_log import OperationRecord


class OperationRecordResponse(BaseModel):
    """Mesmo conjunto de dados exibido na tela de Logs (TASK-056),
    disponível para automações via `GET /api/v1/logs` (TASK-057,
    NFR-006)."""

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime
    tipo_operacao: str
    resultado: str
    duracao_ms: int
    configuracao: str | None = None
    topic: str | None = None
    schema_: str | None = Field(default=None, alias="schema")
    partition: int | None = None
    offset: int | None = None
    key: str | None = None
    erro_tecnico: str | None = None

    @classmethod
    def from_domain(cls, record: OperationRecord) -> "OperationRecordResponse":
        return cls(
            timestamp=record.timestamp,
            tipo_operacao=record.tipo_operacao.value,
            resultado=record.resultado.value,
            duracao_ms=record.duracao_ms,
            configuracao=record.configuracao,
            topic=record.topic,
            schema=record.schema_,
            partition=record.partition,
            offset=record.offset,
            key=record.key,
            erro_tecnico=record.erro_tecnico,
        )
