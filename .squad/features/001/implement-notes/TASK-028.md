# TASK-028 — Implementação

**Story**: US-003a
**Método**: `services/kafka_service.py::validate_payload`

## O que mudou

1. **`app/services/kafka_service.py`**
   - `validate_payload(schema_avsc, payload)` deixou de ser provisório
     (`NotImplementedError`) e passou a orquestrar duas etapas sobre
     `avro/`:
     1. `schema_loader.load_schema(schema_avsc)` (TASK-021) — garante que
        o schema em si é estruturalmente válido, a pré-condição
        documentada de `avro/validator.py`. Se o schema for inválido
        (`AvroSchemaError`), o método já retorna aqui com
        `valid=False` e a `friendly_message` da exceção, sem chegar a
        tentar validar o payload contra um schema quebrado.
     2. `avro_validator.validate_payload(schema_avsc, payload)`
        (TASK-027) — agora sobre um schema já confirmado válido. Cada
        `AvroValidationError` retornada vira um dicionário
        `{"campo":..., "tipo_esperado":..., "tipo_recebido":...}` em
        `PayloadValidationResult.problems` — o mesmo formato de dicionário
        simples já usado em `validate_schema` para `fields` (TASK-022),
        mantendo os contratos de `services/kafka_service.py`
        uniformemente serializáveis (prontos para virar JSON na API sem
        nenhuma camada extra de conversão).
   - Nova função `_record_payload_validation`, no mesmo padrão de
     `_record_connection_test` (TASK-017): grava um Registro de Operação
     via `services/operation_log.py` (TASK-010) — `tipo_operacao=
     VALIDACAO_PAYLOAD`, `resultado`, `duracao_ms` (medido com
     `time.monotonic()`), `schema` (o nome do schema já carregado) e,
     quando inválido, `erro_tecnico` com um resumo técnico de todos os
     problemas (`"campo: esperado 'X', recebido 'Y'; ..."`) — cobrindo
     tanto o caso de múltiplos problemas de payload quanto o caso de
     schema estruturalmente inválido (usa a `friendly_message` como
     `erro_tecnico` quando não há `problems` para resumir). **Toda**
     chamada a `validate_payload` grava um registro, sucesso ou falha —
     nenhum caminho de retorno passa batido pelo histórico.
   - Novo import: `from app.avro import validator as avro_validator`.

2. **Testes — `tests/test_kafka_service.py`**
   Substituído `test_validate_payload_is_provisional` por:
   - `test_validate_payload_returns_valid_for_a_compatible_payload`
   - `test_validate_payload_returns_problems_per_field_for_an_incompatible_payload`
     (cenário 2 de US-003a / FR-013: confirma o dicionário
     `{"campo": "valor", "tipo_esperado": "double", "tipo_recebido": "string"}`)
   - `test_validate_payload_returns_invalid_for_a_malformed_schema_instead_of_raising`
   - `test_validate_payload_records_a_successful_operation` e
     `test_validate_payload_records_a_failed_operation_with_technical_detail`
     (Registro de Operação via TASK-010, incluindo o `schema_` do
     registro e o `erro_tecnico` citando campo/tipos)

Nenhuma alteração foi necessária em `avro/validator.py` (TASK-027),
`avro/schema_loader.py` (TASK-021) nem `services/operation_log.py`
(TASK-010) — todos já expunham exatamente o que `validate_payload`
precisava consumir.

## Definition of Done — verificação

- [x] O método retorna estado de validação e lista de problemas por
      campo quando inválido —
      `test_validate_payload_returns_problems_per_field_for_an_incompatible_payload`
      confirma o formato `{"campo", "tipo_esperado", "tipo_recebido"}`
      por item de `problems`.
- [x] O resultado da validação é gravado como Registro de Operação via
      TASK-010 — `_record_payload_validation` chama
      `operation_log.append_operation_record` em todo caminho de
      retorno (sucesso, payload inválido e schema inválido),
      confirmado por `test_validate_payload_records_a_successful_operation`
      e `test_validate_payload_records_a_failed_operation_with_technical_detail`.

## Checklist

- [x] Unit tests pass — suíte completa: `217 passed` (213 anteriores + 4
      novos testes de `validate_payload`, líquido de 1 teste provisório
      removido; ambiente virtual criado temporariamente para rodar
      `pytest`, removido ao final).
- [x] Integration tests pass — os novos testes já exercitam a integração
      real entre `services/kafka_service.py`, `avro/schema_loader.py`,
      `avro/validator.py` e `services/operation_log.py` (sem nenhum
      dublê/mocks — tudo roda de fato, já que não depende de rede nem de
      um broker Kafka).
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
