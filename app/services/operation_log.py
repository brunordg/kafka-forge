import json
import os
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.config.storage import FILE_MODE, LOGS_DIRNAME, ensure_storage_structure

LOG_FILENAME_PREFIX = "operacoes-"
LOG_FILENAME_SUFFIX = ".jsonl"


class OperationType(str, Enum):
    TESTE_CONEXAO = "teste_conexao"
    TESTE_SCHEMA_REGISTRY = "teste_schema_registry"
    VALIDACAO_SCHEMA = "validacao_schema"
    VALIDACAO_PAYLOAD = "validacao_payload"
    PUBLICACAO = "publicacao"


class OperationResult(str, Enum):
    SUCESSO = "sucesso"
    ERRO = "erro"


class OperationRecord(BaseModel):
    timestamp: datetime
    tipo_operacao: OperationType
    resultado: OperationResult
    duracao_ms: int
    configuracao: str | None = None
    topic: str | None = None
    # "schema_", com alias "schema": nome de atributo Python evita o
    # conflito de `BaseModel.schema()` (método deprecado do Pydantic v1
    # ainda presente por compatibilidade), mantendo a chave JSON fiel ao
    # campo "schema" da tabela "Registro de Operação" (seção 5 do plano).
    schema_: str | None = Field(default=None, alias="schema")
    partition: int | None = None
    offset: int | None = None
    key: str | None = None
    erro_tecnico: str | None = None


def _logs_dir() -> Path:
    base_dir = ensure_storage_structure()
    return base_dir / LOGS_DIRNAME


def _log_file_for_date(target_date: date) -> Path:
    return _logs_dir() / f"{LOG_FILENAME_PREFIX}{target_date:%Y-%m-%d}{LOG_FILENAME_SUFFIX}"


def append_operation_record(
    tipo_operacao: OperationType,
    resultado: OperationResult,
    duracao_ms: int,
    *,
    configuracao: str | None = None,
    topic: str | None = None,
    schema: str | None = None,
    partition: int | None = None,
    offset: int | None = None,
    key: str | None = None,
    erro_tecnico: str | None = None,
    timestamp: datetime | None = None,
) -> OperationRecord:
    record = OperationRecord(
        timestamp=timestamp or datetime.now(timezone.utc),
        tipo_operacao=tipo_operacao,
        resultado=resultado,
        duracao_ms=duracao_ms,
        configuracao=configuracao,
        topic=topic,
        schema=schema,
        partition=partition,
        offset=offset,
        key=key,
        erro_tecnico=erro_tecnico,
    )

    log_file = _log_file_for_date(record.timestamp.date())
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json(by_alias=True))
        handle.write("\n")
    os.chmod(log_file, FILE_MODE)

    return record


def _parse_lines(lines: list[str]) -> list[OperationRecord]:
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(OperationRecord.model_validate_json(line))
        except (json.JSONDecodeError, ValidationError):
            # uma última linha truncada por um encerramento abrupto do
            # processo não deve impedir a leitura do resto do histórico
            continue
    return records


def read_operations_for_date(target_date: date) -> list[OperationRecord]:
    log_file = _log_file_for_date(target_date)
    if not log_file.exists():
        return []
    return _parse_lines(log_file.read_text(encoding="utf-8").splitlines())


def read_recent_operations(limit: int | None = None, days: int = 7) -> list[OperationRecord]:
    log_files = sorted(
        _logs_dir().glob(f"{LOG_FILENAME_PREFIX}*{LOG_FILENAME_SUFFIX}"),
        reverse=True,
    )

    records: list[OperationRecord] = []
    for log_file in log_files[:days]:
        records.extend(_parse_lines(log_file.read_text(encoding="utf-8").splitlines()))
        if limit is not None and len(records) >= limit:
            break

    records.sort(key=lambda record: record.timestamp, reverse=True)
    return records[:limit] if limit is not None else records
