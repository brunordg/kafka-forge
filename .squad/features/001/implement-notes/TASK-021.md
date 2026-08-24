# TASK-021 — Implementação

**Story**: US-002a
**Módulo**: `app/avro/schema_loader.py` (novo)

## O que mudou

1. **`app/avro/schema_loader.py`** (novo arquivo, junto do `.gitkeep`
   pré-existente)
   - `AvroSchemaField` (dataclass: `nome`, `tipo`) e `LoadedAvroSchema`
     (dataclass: `nome`, `namespace`, `fields`, `raw_content`) — formato
     alinhado à entidade "Schema Avro" da seção 5 do plano e ao formato já
     esperado por `services/kafka_service.py::SchemaValidationResult`
     (`nome`, `namespace`, `fields`, `raw_content`), para que uma task
     futura de wiring (TASK-024, que também cobre US-002b/tipos
     complexos) só precise traduzir esse resultado, sem redesenhar nada
     aqui.
   - `load_schema(avsc_content: str) -> LoadedAvroSchema`, função pública
     única do módulo, em quatro passos:
     1. `_parse_json`: `json.loads`; JSON malformado vira `AvroSchemaError`
        (cenário 2 de US-002a) com o `json.JSONDecodeError` original como
        `technical_detail`. JSON válido cujo nível superior não é um
        objeto (ex.: uma lista) também é rejeitado aqui.
     2. `_ensure_is_a_complete_record`: regra de domínio própria (mais
        rígida que a leniência natural do fastavro) — exige `"type":
        "record"` e uma lista `"fields"` presente. Cobre explicitamente o
        edge case da spec de "estrutura de `record` incompleta" (um
        `record` sem `fields` é tolerado silenciosamente pelo fastavro,
        mas é rejeitado aqui com a mensagem "incompleta").
     3. `_validate_with_fastavro`: delega a `fastavro.schema.parse_schema`
        para validação semântica completa (tipo desconhecido, `name`
        ausente, campo sem `name`/`type` etc.). Como o fastavro levanta
        tipos de exceção heterogêneos para entrada malformada
        (`UnknownType`, `SchemaParseException`, e até `KeyError`/
        `TypeError`/`AttributeError` "crus" — confirmado experimentalmente
        durante a implementação), a captura é deliberadamente ampla
        (`except Exception`) só ao redor dessa única chamada, sempre
        traduzida em `AvroSchemaError` — nunca deixando um `.avsc`
        inválido travar a aplicação nem ser aceito silenciosamente
        (cenário 3 de US-002a / edge case da spec).
     4. Extração final de `nome`/`namespace`/`fields` a partir do JSON
        original (não do dicionário devolvido por `parse_schema`, que
        qualifica `name` com o namespace — confirmado que `parse_schema`
        não muta o dicionário de entrada, então o `raw_schema` original
        continua confiável como fonte para nome/namespace "crus").
   - `_format_type`: para tipos simples (string, int, long, float, double,
     boolean, bytes, null), devolve o nome do tipo diretamente. Tipos
     compostos (union/array/map/enum/record aninhado) só recebem uma
     representação bruta (`json.dumps`) por ora — a formatação amigável e
     recursiva deles é escopo explícito de US-002b, fora desta task.

Nenhuma outra camada foi tocada: `services/kafka_service.py::validate_schema`
continua com `NotImplementedError` (seu wiring a `avro/schema_loader.py`
é de uma task futura), e `ui/`/`api/` continuam sem importar `avro/`
diretamente, preservando a regra de camadas verificada por
`tests/test_architecture_boundaries.py`.

2. **Testes — `tests/test_schema_loader.py`** (novo arquivo)
   14 casos cobrindo os três cenários do DoD:
   - Cenário 1 (schema válido, tipos simples): nome/namespace/campos
     extraídos corretamente para os sete tipos primitivos testáveis
     (`long`, `string`, `double`, `int`, `float`, `boolean`, `bytes`),
     preservação do `raw_content` original, `namespace` ausente vira
     `None`, e um `record` com `fields: []` é aceito.
   - Cenário 2 (JSON malformado): mensagem compreensível e detalhe
     técnico presentes; nenhum `json.JSONDecodeError` cru escapa.
   - Cenário 3 / edge case (JSON válido, Avro inválido): nível superior
     que não é objeto, `type` diferente de `record`, `record` sem
     `fields` (mensagem menciona "incompleta"), `record` sem `name`,
     tipo de campo desconhecido (nome do tipo inválido aparece no
     `technical_detail`), campo sem `type`, campo sem `name`, e `fields`
     que não é uma lista — todos rejeitados com `AvroSchemaError`, sem
     lançar exceções brutas do Python.

## Definition of Done — verificação

- [x] Um `.avsc` válido com tipos simples retorna nome, namespace, campos
      e tipos corretamente (cenário 1) —
      `test_valid_schema_with_simple_types_extracts_name_namespace_and_fields`
      e testes correlatos.
- [x] Um `.avsc` com estrutura JSON inválida é rejeitado com mensagem
      compreensível (cenário 2) —
      `test_malformed_json_is_rejected_with_an_understandable_message`.
- [x] Um `.avsc` sintaticamente válido como JSON mas semanticamente
      inválido como Avro (tipo desconhecido, `record` incompleto) é
      rejeitado com explicação, sem travar nem ser aceito silenciosamente
      (cenário 3) — cobertura completa na seção "edge case" dos testes.

## Checklist

- [x] Unit tests pass — suíte completa: `168 passed` (154 anteriores + 14
      novos testes de `tests/test_schema_loader.py`; ambiente virtual
      criado temporariamente para rodar `pytest`, removido ao final).
- [x] Integration tests pass — não há integração externa nesta task (só
      parsing/validação local em memória); a suíte completa (que inclui
      os testes de arquitetura, API e UI já existentes) permanece verde,
      confirmando que o novo módulo não quebrou nada.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
