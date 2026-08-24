# TASK-029 — Implementação

**Story**: US-003a
**Rota**: `POST /api/v1/messages/validate`

## O que mudou

1. **`app/api/schemas/messages.py`** (novo arquivo)
   - `PayloadValidateRequest(avsc_content: str, payload: dict)`, com a
     mesma validação de "não pode ficar vazio" para `avsc_content` já
     usada em `SchemaValidateRequest` (TASK-022).
   - `PayloadProblemResponse(campo, tipo_esperado, tipo_recebido)` — o
     contrato HTTP do dicionário `{"campo":..., "tipo_esperado":...,
     "tipo_recebido":...}` que `services/kafka_service.py::validate_payload`
     já produz em `PayloadValidationResult.problems` (TASK-028). É o
     **mesmo formato** que qualquer tela (a futura `ui/pages/publicar_mensagem.py`)
     vai consumir, porque ambas as camadas leem o mesmo
     `PayloadValidationResult` — não existe uma segunda definição desse
     formato em lugar nenhum (DoD: "retorna o mesmo formato de erro... usado
     pela UI").
   - `PayloadValidationResponse(valid, message, problems)`, com
     `from_domain(result: PayloadValidationResult)`, no mesmo padrão de
     `SchemaValidationResponse.from_domain` (TASK-022) e
     `ConnectionTestResponse.from_domain` (TASK-018).

2. **`app/api/routes/messages.py`** (novo arquivo)
   `POST /validate` (montado sob o prefixo `/messages`), chamando
   exclusivamente `kafka_service.validate_payload` — nenhuma outra
   dependência de `avro/`, `kafka/` ou `config/manager.py` diretamente
   (verificado por `tests/test_architecture_boundaries.py`). Como
   `kafka_service.validate_payload` nunca constrói um `Producer` nem um
   `AdminClient` (só chama `avro/schema_loader.py` e `avro/validator.py`,
   ambos puramente locais/em memória), a ausência de publicação no Kafka é
   garantida estruturalmente, não por uma checagem defensiva na rota.

3. **`app/api/routes/__init__.py`**
   Registrado `messages_router` em `api_router` (rota final:
   `/api/v1/messages/validate`).

4. **Testes — `tests/test_messages_route.py`** (novo arquivo)
   6 casos:
   - `test_validate_payload_route_returns_valid_for_a_compatible_payload`
   - `test_validate_payload_route_returns_the_same_field_type_error_shape_used_by_the_ui`
     (cenário 2 de US-003a / FR-013): confirma o dicionário exato
     `{"campo": "valor", "tipo_esperado": "double", "tipo_recebido": "string"}`.
   - `test_validate_payload_route_returns_a_structured_error_for_a_malformed_schema`:
     `200` com `valid: false`, não um `500` genérico.
   - `test_validate_payload_route_with_empty_avsc_content_returns_422`
   - `test_validate_payload_route_never_touches_kafka`: monkeypatcha
     `kafka_service.kafka_connection.build_producer` **e**
     `build_admin_client` para provar, por observação direta, que nenhum
     dos dois é chamado ao validar um payload (DoD: nenhuma publicação no
     Kafka ocorre).
   - `test_messages_route_is_documented_in_openapi_schema`

Nenhuma alteração foi necessária em `services/kafka_service.py`
(TASK-028) — a rota só expõe `validate_payload`, já implementado.

## Definition of Done — verificação

- [x] A rota valida um payload contra um schema e retorna o mesmo formato
      de erro (campo/tipo esperado/tipo recebido) usado pela UI — o
      formato vem de `PayloadValidationResult.problems`, a única fonte de
      verdade compartilhada entre UI e API (NFR-006); confirmado por
      `test_validate_payload_route_returns_the_same_field_type_error_shape_used_by_the_ui`.
- [x] Nenhuma publicação no Kafka ocorre ao chamar esta rota — garantido
      estruturalmente (o caminho de código de `validate_payload` nunca
      toca `kafka/`) e confirmado por observação em
      `test_validate_payload_route_never_touches_kafka`.

## Checklist

- [x] Unit tests pass — suíte completa: `223 passed` (217 anteriores + 6
      novos testes de `tests/test_messages_route.py`; ambiente virtual
      criado temporariamente para rodar `pytest`, removido ao final).
- [x] Integration tests pass — cobertos pelos testes de rota via
      `fastapi.testclient` (fixture `api_client`), exercitando a pilha
      completa API → `services/kafka_service.py` →
      `avro/schema_loader.py` → `avro/validator.py`.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
