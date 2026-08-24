import stat
from datetime import date, datetime, timezone

from app.services.operation_log import (
    LOG_FILENAME_PREFIX,
    LOG_FILENAME_SUFFIX,
    OperationResult,
    OperationType,
    _logs_dir,
    append_operation_record,
    read_operations_for_date,
    read_recent_operations,
)


def _dt(day: str, hour: int = 12, minute: int = 0) -> datetime:
    year, month, day_ = (int(part) for part in day.split("-"))
    return datetime(year, month, day_, hour, minute, tzinfo=timezone.utc)


def test_append_creates_file_named_after_the_operation_day():
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=120,
        configuracao="Desenvolvimento",
        timestamp=_dt("2026-08-22"),
    )

    expected_file = _logs_dir() / f"{LOG_FILENAME_PREFIX}2026-08-22{LOG_FILENAME_SUFFIX}"
    assert expected_file.exists()


def test_append_restricts_log_file_permissions():
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=10,
        timestamp=_dt("2026-08-22"),
    )

    log_file = _logs_dir() / f"{LOG_FILENAME_PREFIX}2026-08-22{LOG_FILENAME_SUFFIX}"
    assert stat.S_IMODE(log_file.stat().st_mode) == 0o600


def test_append_record_contains_all_fr024_minimum_fields():
    append_operation_record(
        OperationType.PUBLICACAO,
        OperationResult.ERRO,
        duracao_ms=340,
        configuracao="Desenvolvimento",
        topic="pedido-criado",
        schema="Pedido",
        erro_tecnico="Tópico inexistente no cluster",
        timestamp=_dt("2026-08-22"),
    )

    [record] = read_operations_for_date(date(2026, 8, 22))

    assert record.timestamp == _dt("2026-08-22")
    assert record.tipo_operacao is OperationType.PUBLICACAO
    assert record.configuracao == "Desenvolvimento"
    assert record.topic == "pedido-criado"
    assert record.schema_ == "Pedido"
    assert record.resultado is OperationResult.ERRO
    assert record.duracao_ms == 340
    assert record.erro_tecnico == "Tópico inexistente no cluster"


def test_append_record_stores_partition_offset_and_key_when_applicable():
    append_operation_record(
        OperationType.PUBLICACAO,
        OperationResult.SUCESSO,
        duracao_ms=95,
        configuracao="Desenvolvimento",
        topic="pedido-criado",
        schema="Pedido",
        partition=2,
        offset=12345,
        key="pedido-123",
        timestamp=_dt("2026-08-22"),
    )

    [record] = read_operations_for_date(date(2026, 8, 22))

    assert record.partition == 2
    assert record.offset == 12345
    assert record.key == "pedido-123"
    assert record.erro_tecnico is None


def test_multiple_appends_on_the_same_day_accumulate_without_overwriting():
    for i in range(3):
        append_operation_record(
            OperationType.VALIDACAO_PAYLOAD,
            OperationResult.SUCESSO,
            duracao_ms=10 + i,
            timestamp=_dt("2026-08-22", hour=10 + i),
        )

    records = read_operations_for_date(date(2026, 8, 22))

    assert len(records) == 3
    assert [r.duracao_ms for r in records] == [10, 11, 12]


def test_appends_on_different_days_do_not_touch_previous_days_file():
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=50,
        timestamp=_dt("2026-08-21"),
    )
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=60,
        timestamp=_dt("2026-08-22"),
    )

    day_21 = read_operations_for_date(date(2026, 8, 21))
    day_22 = read_operations_for_date(date(2026, 8, 22))

    assert len(day_21) == 1
    assert day_21[0].duracao_ms == 50
    assert len(day_22) == 1
    assert day_22[0].duracao_ms == 60


def test_read_operations_for_date_without_any_record_returns_empty_list():
    assert read_operations_for_date(date(2026, 1, 1)) == []


def test_append_without_explicit_timestamp_uses_current_time():
    before = datetime.now(timezone.utc)
    record = append_operation_record(
        OperationType.TESTE_SCHEMA_REGISTRY,
        OperationResult.SUCESSO,
        duracao_ms=15,
    )
    after = datetime.now(timezone.utc)

    assert before <= record.timestamp <= after
    assert read_operations_for_date(record.timestamp.date()) == [record]


def test_read_recent_operations_orders_newest_first_across_days():
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=1,
        timestamp=_dt("2026-08-20"),
    )
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=2,
        timestamp=_dt("2026-08-21"),
    )
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=3,
        timestamp=_dt("2026-08-22"),
    )

    records = read_recent_operations()

    assert [r.duracao_ms for r in records] == [3, 2, 1]


def test_read_recent_operations_respects_limit():
    for day, duracao in [("2026-08-20", 1), ("2026-08-21", 2), ("2026-08-22", 3)]:
        append_operation_record(
            OperationType.TESTE_CONEXAO,
            OperationResult.SUCESSO,
            duracao_ms=duracao,
            timestamp=_dt(day),
        )

    records = read_recent_operations(limit=2)

    assert [r.duracao_ms for r in records] == [3, 2]


def test_read_recent_operations_ignores_files_older_than_days_window():
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=1,
        timestamp=_dt("2026-08-01"),
    )
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=2,
        timestamp=_dt("2026-08-22"),
    )

    records = read_recent_operations(days=1)

    assert [r.duracao_ms for r in records] == [2]


def test_read_operations_skips_a_corrupted_trailing_line():
    append_operation_record(
        OperationType.TESTE_CONEXAO,
        OperationResult.SUCESSO,
        duracao_ms=42,
        timestamp=_dt("2026-08-22"),
    )
    log_file = _logs_dir() / f"{LOG_FILENAME_PREFIX}2026-08-22{LOG_FILENAME_SUFFIX}"
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write('{"timestamp": "2026-08-22T13:00:00Z", "tipo_ope')  # linha truncada

    records = read_operations_for_date(date(2026, 8, 22))

    assert len(records) == 1
    assert records[0].duracao_ms == 42
