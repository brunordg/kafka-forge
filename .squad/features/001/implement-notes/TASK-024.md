# TASK-024 — Implementação

**Story**: US-002b
**Módulo**: `app/avro/schema_loader.py`

## O que mudou

1. **`app/avro/schema_loader.py`**
   `_format_type` deixou de cair direto no `json.dumps` bruto para
   qualquer tipo não-string (comportamento provisório da TASK-021) e
   passou a formatar recursivamente os cinco tipos compostos exigidos por
   US-002b:
   - `_format_union(tipos)`: uma lista Avro (`["A", "B", ...]`) vira
     `"A | B | ..."`. Caso especial — o motivo desta task — quando a
     união tem exatamente dois membros e um deles é `"null"` (o padrão de
     campo opcional, ex.: `["null", "string"]`), o resultado é `"string
     (opcional)"` em vez da união bruta ilegível; funciona
     independentemente da posição de `"null"` na lista.
   - `_format_enum(tipo)`: `{"type": "enum", "name": "Status", "symbols":
     [...]}` vira `"enum<Status>(NOVO, PAGO, CANCELADO)"`.
   - `_format_array(tipo)`: `{"type": "array", "items": ...}` vira
     `"array<...>"`, com o tipo do item formatado recursivamente (incluindo
     um `array` de `record`, testado explicitamente).
   - `_format_map(tipo)`: `{"type": "map", "values": ...}` vira
     `"map<...>"`, com o tipo do valor formatado recursivamente.
   - `_format_record(tipo)`: um `record` aninhado (não o schema de
     nível superior, mas um `record` usado como tipo de um campo) vira
     `"record<Nome>{campo1: tipo1, campo2: tipo2}"`, com cada campo
     interno também formatado recursivamente — é isso que torna a
     formatação "recursiva" de fato: um `array` de `record` com um campo
     `union` opcional, por exemplo, se resolve corretamente em cascata.
   - Dispatcher `_format_type`: string → devolvida como está (tipo
     primitivo ou referência a tipo nomeado); lista → `_format_union`;
     dicionário → consulta `_COMPOSITE_TYPE_FORMATTERS` pelo valor de
     `"type"`; dicionário sem correspondência mas com chave `"type"`
     (ex.: `{"type": "string"}`, `logicalType`) recorre sobre esse valor;
     qualquer outra forma inesperada cai no mesmo fallback bruto e seguro
     (`json.dumps`) já usado na TASK-021 — nunca trava, mesmo que um
     schema já validado pelo fastavro tenha uma forma que os
     formatadores acima não previram.
   - `load_schema` (docstring atualizada para citar também US-002b) e
     `_extract_fields` não precisaram de nenhuma mudança de assinatura —
     só a implementação de `_format_type` ficou mais rica, mantendo o
     restante do pipeline (parse → validação estrutural → validação
     fastavro → extração) intacto.

Nenhuma outra camada foi tocada: `services/kafka_service.py`,
`api/routes/schema.py` e `ui/pages/schemas_avro.py` (TASK-022/TASK-023)
continuam funcionando sem alteração, já que só consomem
`AvroSchemaField.tipo` como string — a riqueza da formatação chega a eles
de graça.

2. **Testes — `tests/test_schema_loader.py`**
   5 novos casos, na seção "cenário único de US-002b":
   - `test_schema_with_all_five_composite_types_is_loaded_and_formatted_correctly`:
     um único schema com union opcional, enum, array, map e record
     aninhado — todos os campos e tipos formatados corretamente de uma
     vez, fiel ao cenário único do Acceptance Scenario de US-002b.
   - `test_optional_field_null_string_union_is_formatted_as_readable_not_a_raw_union`:
     `["null", "string"]` vira `"string (opcional)"`, sem colchetes
     sobrando (prova explícita de que não é mais a união bruta).
   - `test_optional_field_with_null_as_second_member_is_formatted_the_same_way`:
     `["string", "null"]` produz o mesmo resultado, independente da
     posição de `null`.
   - `test_union_without_null_is_formatted_with_a_readable_separator`:
     uma união sem `null` (`["int", "long"]`) vira `"int | long"`.
   - `test_array_of_a_record_is_formatted_recursively`: um `array` cujo
     item é um `record` vira `"array<record<Item>{sku: string}>"`,
     provando a recursão entre formatadores (não só formatação de um
     nível).

## Definition of Done — verificação

- [x] Um schema contendo os cinco tipos compostos listados é carregado e
      todos os campos/tipos são exibidos corretamente (cenário único do
      Acceptance Scenario de US-002b) —
      `test_schema_with_all_five_composite_types_is_loaded_and_formatted_correctly`.
- [x] O campo opcional `["null", "string"]` é formatado de forma legível
      (não como union bruta ilegível) —
      `test_optional_field_null_string_union_is_formatted_as_readable_not_a_raw_union`
      e o teste simétrico com `null` na segunda posição.

## Checklist

- [x] Unit tests pass — suíte completa: `185 passed` (180 anteriores + 5
      novos testes de `tests/test_schema_loader.py`; ambiente virtual
      criado temporariamente para rodar `pytest`, removido ao final).
- [x] Integration tests pass — não há integração externa nesta task; a
      suíte completa (incluindo os testes de rota `/schema/validate` e da
      página `schemas_avro.py`, que consomem `avro/schema_loader.py`
      indiretamente via `services/kafka_service.py`) permanece verde,
      confirmando que a formatação mais rica não quebrou nada a jusante.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
