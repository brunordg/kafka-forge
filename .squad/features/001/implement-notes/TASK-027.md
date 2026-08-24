# TASK-027 — Implementação

**Story**: US-003a
**Módulo**: `app/avro/validator.py` (novo)

## O que mudou

1. **`app/avro/schema_loader.py`** (pequeno refactor de suporte)
   `_format_type` foi renomeada para `format_type` (pública) — nenhuma
   mudança de comportamento, só de visibilidade. Motivo: `avro/validator.py`
   precisa descrever o "tipo esperado" de cada campo (FR-013) na mesma
   forma legível já construída por `schema_loader.py` para US-002b (ex.:
   `"string (opcional)"`, `"double"`), e reaproveitar essa função pública é
   a alternativa a duplicar a lógica de formatação recursiva entre os
   dois módulos do pacote `avro/`. Nenhum teste referenciava o nome
   privado diretamente, então o rename não quebrou nada.

2. **`app/avro/validator.py`** (novo arquivo)
   - `validate_payload(avsc_content: str, payload: dict) -> list[AvroValidationError]`:
     usa `fastavro.validate` **por campo** (não sobre o registro inteiro
     de uma vez) para poder coletar **todos** os problemas do payload,
     não só o primeiro — decisão tomada porque, testado empiricamente
     durante a implementação, `fastavro.validate(datum, schema,
     raise_errors=True)` sobre o schema inteiro para no primeiro erro
     encontrado, o que não bastaria para o cenário 4 (campo extra e
     campo obrigatório ausente coexistindo no mesmo payload, ambos
     precisam aparecer).
   - `_validate_known_fields`: para cada campo do schema, valida
     `payload.get(nome)` contra o tipo do campo com
     `fastavro.validate(..., raise_errors=False)`. Um campo ausente é
     tratado como `None` — a mesma convenção que o próprio
     `fastavro.validate` usa nativamente para o registro inteiro, que é
     exatamente o que faz um campo `["null", "string"]` ausente ser
     aceito de graça (cenário 3 / edge case da spec), sem nenhum código
     especial: `None` é um valor válido para qualquer união com `null`,
     e inválido para um tipo não anulável — que é como um campo
     obrigatório ausente vira um problema (`tipo_recebido="ausente"`,
     distinto de um `null` explícito).
   - `_validate_no_extra_fields`: fastavro **não rejeita chaves extras**
     no payload por padrão (confirmado empiricamente) — por isso esta
     função própria compara as chaves do payload contra os nomes de
     campo do schema e sinaliza cada uma não prevista (cenário 4).
   - `_received_type_name(value)`: mapeia o valor Python já decodificado
     do JSON (`None`, `bool`, `int`, `float`, `str`, `bytes`, `list`,
     `dict`) para um nome de tipo Avro legível (`"null"`, `"boolean"`,
     `"int"`, `"double"`, `"string"`, `"bytes"`, `"array"`, `"record"`),
     usado como `tipo_recebido`.
   - Cada problema é um `AvroValidationError.field_type_mismatch(campo,
     tipo_esperado, tipo_recebido)` (TASK-026) — **construído, não
     levantado**: a exceção é reaproveitada como carregador de dado
     estruturado (`campo`/`tipo_esperado`/`tipo_recebido` +
     `friendly_message` pronta), coletada em uma lista. Lista vazia
     = payload válido. Isso evita criar uma segunda estrutura de dados
     paralela (`PayloadValidationProblem` ou similar) só para repetir os
     mesmos três campos que `AvroValidationError` já expõe.
   - Payload que não é um objeto JSON (ex.: uma lista no nível superior)
     não trava: vira um único problema com `campo="(payload)"`,
     `tipo_esperado="record"`, `tipo_recebido` derivado do valor
     recebido.
   - Pressupõe que o `.avsc` recebido já é estruturalmente válido
     (checado por `avro/schema_loader.py::load_schema` antes desta
     chamada, no fluxo real de `services/kafka_service.py` — wiring de
     uma task futura) — esta função só valida o *payload*, documentado
     explicitamente na docstring.

3. **Testes — `tests/test_validator.py`** (novo arquivo)
   12 casos cobrindo os quatro cenários do DoD:
   - Cenário 1: payload compatível (com e sem o campo opcional presente)
     não tem problemas.
   - Cenário 2: texto em campo numérico aponta `campo="valor"`,
     `tipo_esperado="double"`, `tipo_recebido="string"`, com mensagem
     amigável citando os três.
   - Cenário 3: campo opcional `["null", "string"]` aceito tanto
     explicitamente `null` quanto com o tipo alternativo (`string`);
     um valor de tipo realmente incompatível (`int`) nesse mesmo campo
     ainda é sinalizado, com `tipo_esperado="string (opcional)"`.
   - Cenário 4: campo obrigatório ausente (`tipo_recebido="ausente"`) e
     campo extra não previsto, isolados e também coexistindo no mesmo
     payload; e coexistindo com um erro de tipo em outro campo.
   - Extra: payload que não é um objeto JSON não trava, vira um problema
     estruturado.

## Definition of Done — verificação

- [x] Um payload compatível com o schema é confirmado como válido
      (cenário 1) — `test_compatible_payload_has_no_problems` e
      `test_compatible_payload_with_optional_field_omitted_has_no_problems`.
- [x] Um payload com tipo incompatível aponta campo, tipo esperado e tipo
      recebido (cenário 2) —
      `test_text_in_a_numeric_field_is_flagged_with_field_and_types`.
- [x] Um campo opcional `["null", "string"]` aceita corretamente tanto
      ausência quanto o tipo alternativo (cenário 3) —
      `test_optional_field_explicitly_null_is_accepted` e
      `test_optional_field_with_the_alternative_type_is_accepted`.
- [x] Campos extras não previstos no schema e campos obrigatórios
      ausentes são ambos sinalizados como inválidos (cenário 4) —
      `test_missing_required_field_is_flagged`,
      `test_extra_field_not_in_schema_is_flagged` e
      `test_missing_field_and_extra_field_are_both_flagged_together`.

## Checklist

- [x] Unit tests pass — suíte completa: `213 passed` (201 anteriores + 12
      novos testes de `tests/test_validator.py`; ambiente virtual criado
      temporariamente para rodar `pytest`, removido ao final).
- [x] Integration tests pass — não há integração externa nesta task; a
      suíte completa (incluindo `tests/test_architecture_boundaries.py` e
      todos os testes de `avro/schema_loader.py` que dependem de
      `format_type`) permanece verde após o rename.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
