# TASK-022 — Implementação

**Story**: US-002a
**Rota**: `POST /api/v1/schema/validate`

## O que mudou

1. **`app/services/kafka_service.py`** (wiring necessário para a rota
   funcionar — sem isso, `validate_schema` continuava com
   `NotImplementedError`, o que violaria o DoD "não é um erro 500
   genérico")
   `validate_schema(avsc_content)` deixou de ser provisório e passou a
   delegar a `avro.schema_loader.load_schema` (TASK-021):
   - Em caso de `AvroSchemaError`, devolve
     `SchemaValidationResult(valid=False, message=error.friendly_message)`
     — **nunca propaga a exceção**, seguindo o mesmo padrão de
     `test_connection` (TASK-017) de sempre retornar um resultado
     estruturado, nunca deixar um erro de domínio virar uma exceção não
     tratada na camada de serviço.
   - Em caso de sucesso, devolve `SchemaValidationResult(valid=True, ...)`
     com `nome`, `namespace`, `fields` (lista de `{"nome":..., "tipo":...}`,
     a partir dos `AvroSchemaField` de `avro/schema_loader.py`) e
     `raw_content`.
   - A formatação recursiva amigável de tipos compostos (US-002b) fica
     documentada como escopo futuro (TASK-024), sem necessidade de
     alterar esta função quando isso for implementado — só
     `avro/schema_loader.py` muda.
   - Nenhum Registro de Operação é gravado aqui: o DoD desta task não pede
     isso (diferente de `test_connection`, cujo DoD explícito exigia
     TASK-010); adicionar logging especulativo seria além do escopo
     pedido (constituição, princípio II).

2. **`app/api/schemas/schema.py`** (novo arquivo)
   - `SchemaValidateRequest(avsc_content: str)`, com validação de que o
     conteúdo não pode ficar vazio (mesmo padrão de
     `ConfigurationCreateRequest._nome_obrigatorio`).
   - `SchemaFieldResponse(nome, tipo)` e `SchemaValidationResponse(valid,
     message, nome, namespace, fields, raw_content)`, com
     `from_domain(result: SchemaValidationResult)` — mesmo padrão de
     `ConnectionTestResponse.from_domain` (TASK-018).

3. **`app/api/routes/schema.py`** (novo arquivo)
   `POST /validate` (montado sob o prefixo `/schema`), chamando
   exclusivamente `kafka_service.validate_schema` e devolvendo
   `SchemaValidationResponse` documentado via `response_model`. Como
   `validate_schema` nunca propaga `AvroSchemaError`, a rota não precisa
   de nenhum bloco `try/except` — um `.avsc` inválido sempre vira `200 OK`
   com `valid: false` e uma `message` compreensível, nunca um `500`
   genérico (DoD).

4. **`app/api/routes/__init__.py`**
   Registrado `schema_router` em `api_router`, sob o prefixo `/api/v1`
   (rota final: `/api/v1/schema/validate`).

5. **Testes**
   - `tests/test_kafka_service.py`: substituídos
     `test_validate_schema_is_provisional` por
     `test_validate_schema_returns_a_valid_result_for_a_well_formed_avsc`
     e `test_validate_schema_returns_an_invalid_result_instead_of_raising`.
   - `tests/test_schema_route.py` (novo arquivo): cobre schema válido
     (retorna nome/namespace/campos), JSON malformado (erro estruturado,
     `200` com `valid: false`), estrutura semanticamente inválida
     (`record` sem `fields`, mensagem menciona "incompleta"), corpo com
     `avsc_content` vazio (`422`, validação do próprio contrato Pydantic)
     e presença da rota no `openapi.json`.

## Definition of Done — verificação

- [x] A rota aceita um `.avsc` e retorna nome/namespace/campos/tipos ou
      erro compreensível, via `services/kafka_service.py` — a rota só
      chama `kafka_service.validate_schema`, nunca `avro/` diretamente
      (verificado por `tests/test_architecture_boundaries.py`).
- [x] Casos de schema inválido retornam um erro estruturado, não um erro
      500 genérico — `validate_schema` nunca propaga `AvroSchemaError`
      (sempre devolve `SchemaValidationResult`), então a rota sempre
      responde `200` com `valid`/`message` no corpo; confirmado por
      `test_validate_schema_route_returns_a_structured_error_for_malformed_json`
      e `test_validate_schema_route_returns_a_structured_error_for_a_semantically_invalid_avro_schema`.

## Checklist

- [x] Unit tests pass — suíte completa: `174 passed` (168 anteriores + 2
      novos testes de `validate_schema` em `test_kafka_service.py` + 5
      novos testes de rota em `test_schema_route.py`, líquido de 1 teste
      provisório removido; ambiente virtual criado temporariamente para
      rodar `pytest`, removido ao final).
- [x] Integration tests pass — cobertos pelos testes de rota via
      `fastapi.testclient` (fixture `api_client`), exercitando a pilha
      completa API → `services/kafka_service.py` →
      `avro/schema_loader.py`.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
