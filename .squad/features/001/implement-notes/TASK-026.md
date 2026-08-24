# TASK-026 — Implementação

**Story**: US-003a
**Classe**: `app/exceptions.py::AvroValidationError`

## O que mudou

1. **`app/exceptions.py`**
   `AvroValidationError` já existia na hierarquia de exceções de domínio
   (skeleton criado em uma task anterior), mas apenas como subclasse
   simples de `KafkaForgeError` (`pass`), sem nada além de
   `friendly_message`/`technical_detail`. Isso não bastava para FR-013:
   validar um payload precisa apontar **qual campo** está incorreto, o
   **tipo esperado** e o **tipo recebido**, de forma estruturada — não só
   embutido em uma frase.

   A classe passou a:
   - Sobrescrever `__init__` para aceitar três atributos estruturados
     opcionais, mantidos como `keyword-only` para não quebrar a
     compatibilidade com a chamada posicional `(friendly_message,
     technical_detail)` já usada nos testes parametrizados existentes
     (`ALL_EXCEPTION_TYPES`, em `tests/test_exceptions.py`): `campo`,
     `tipo_esperado`, `tipo_recebido` (todos `str | None`, default
     `None`).
   - Ganhar o classmethod `field_type_mismatch(campo, tipo_esperado,
     tipo_recebido, technical_detail="")`, no mesmo padrão de
     `KafkaAuthenticationError.missing_client_key_password` (TASK-016):
     uma fábrica dedicada para o caso mandatado explicitamente pela spec
     (cenário 2 de US-003a: "a ferramenta informa qual campo está
     incorreto, o tipo esperado e o tipo recebido"), gerando uma
     `friendly_message` que já cita os três dados
     ("O campo 'valor' está incorreto: era esperado o tipo 'double', mas
     foi recebido 'string'.") e preenchendo os três atributos estruturados
     ao mesmo tempo.

   Essa é a mesma peça que `services/kafka_service.py::PayloadValidationResult.problems`
   (já definido como `list[dict]`) vai consumir quando `avro/validator.py`
   (TASK-027) e o wiring de `validate_payload` (TASK-028) forem
   implementados: cada `AvroValidationError.field_type_mismatch(...)`
   capturada lá vira um item `{"campo":..., "tipo_esperado":...,
   "tipo_recebido":...}` sem nenhuma lógica nova de extração — os
   atributos já vêm prontos na exceção.

2. **Testes — `tests/test_exceptions.py`**
   7 novos casos, na seção "FR-013 / US-003a", isolados de
   `app/avro/validator.py` e de qualquer schema/payload real (o módulo
   ainda não existe — é a TASK-027):
   - `test_avro_validation_error_structured_fields_default_to_none`:
     construtor genérico (só `friendly_message`) deixa `campo`/
     `tipo_esperado`/`tipo_recebido` como `None`.
   - `test_field_type_mismatch_is_an_avro_validation_error`
   - `test_field_type_mismatch_carries_the_structured_detail`: os três
     atributos estruturados batem com os argumentos passados.
   - `test_field_type_mismatch_identifies_the_field_in_the_friendly_message`:
     campo, tipo esperado e tipo recebido aparecem na mensagem amigável.
   - `test_field_type_mismatch_carries_the_given_technical_detail` e
     `test_field_type_mismatch_technical_detail_defaults_to_empty_string`
   - `test_field_type_mismatch_can_be_raised_and_caught_normally`

   Os testes parametrizados pré-existentes
   (`test_exception_exposes_friendly_message_and_technical_detail`,
   `test_exception_is_subclass_of_kafkaforge_error`) continuam cobrindo
   `AvroValidationError` sem alteração, já que a assinatura posicional
   original permanece compatível.

## Definition of Done — verificação

- [x] A exceção carrega, no detalhe estruturado, o campo problemático, o
      tipo esperado e o tipo recebido (FR-013) —
      `test_field_type_mismatch_carries_the_structured_detail` confirma
      `error.campo`, `error.tipo_esperado` e `error.tipo_recebido`.

## Checklist

- [x] Unit tests pass — suíte completa: `201 passed` (194 anteriores + 7
      novos testes de `AvroValidationError`; ambiente virtual criado
      temporariamente para rodar `pytest`, removido ao final).
- [x] Integration tests pass — não há integração externa nesta task (só a
      própria classe de exceção); confirmado por busca no código que
      nenhum outro módulo levanta `AvroValidationError` ainda (será
      `avro/validator.py`, TASK-027).
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
