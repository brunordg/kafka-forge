# TASK-025 — Implementação

**Story**: US-002b
**Componente**: `app/ui/components/avro_type.py` (novo)

## O que mudou

1. **`app/ui/components/avro_type.py`** (novo arquivo, primeiro módulo do
   diretório `app/ui/components/`, até então só com o `.gitkeep`)
   - `render(tipo: str) -> None`: recebe a string de tipo **já formatada**
     por `avro/schema_loader.py` (TASK-024 — ex.: `"string (opcional)"`,
     `"enum<Status>(NOVO, PAGO)"`, `"array<string>"`, `"map<string>"`,
     `"record<Endereco>{rua: string}"`) e decide *como exibi-la*: os
     cinco tipos compostos suportados (union opcional, union genérica,
     enum, array, map, record — FR-010) ganham um `ui.badge` colorido
     (`mark("avro-type-badge")`); um tipo primitivo simples (string, int,
     long, float, double, boolean, bytes, null) vira um `ui.label` comum
     (`mark("avro-type-label")`).
   - `_badge_color(tipo)`: classificação pura (sem NiceGUI), só olhando
     para a *forma* da string já pronta — sufixo `" (opcional)"`,
     prefixos `"enum<"`/`"array<"`/`"map<"`/`"record<"`, ou a presença de
     `" | "` para união genérica sem `null`. Não reconstrói nem duplica
     nenhuma regra de formatação de `avro/schema_loader.py` — a
     construção da própria string (ex.: como um `record` aninhado vira
     `"record<Nome>{...}"`) continua existindo em um único lugar; este
     componente só reage à forma final.
   - Cores por categoria: `opcional` → `blue-grey`, `enum` → `orange`,
     `array` → `green`, `map` → `teal`, `record` → `indigo`, `union`
     genérica → `purple`.

2. **`app/ui/pages/schemas_avro.py`**
   O laço que antes montava `ui.label(f"{campo['nome']}: {campo['tipo']}")`
   como uma única string passou a usar o componente: `ui.label(f"{campo['nome']}:")`
   seguido de `avro_type.render(campo["tipo"])`, dentro do mesmo `ui.row()`.
   Esta é a única mudança de comportamento visível na tela: tipos
   compostos agora aparecem com um selo colorido em vez de texto corrido.

3. **Testes**
   - `tests/test_avro_type_component.py` (novo arquivo): 8 testes unitários
     de `_badge_color`, cobrindo os cinco tipos compostos, a união
     genérica sem `null`, todos os tipos primitivos (sem selo) e um caso
     de tipo composto aninhado (`array<record<...>>`, classificado pelo
     prefixo mais externo).
   - `tests/test_schemas_avro_page.py`:
     - Ajustado `test_uploading_a_valid_avsc_shows_name_namespace_fields_and_raw_content`,
       que antes checava a string combinada `"id: long"` num único
       elemento; agora checa `"id:"` e, separadamente, o tipo `"long"`
       com `marker="avro-type-label"` — refletindo a divisão real em
       dois elementos após a extração do componente.
     - Novo teste
       `test_the_five_composite_types_are_rendered_via_the_shared_component`:
       envia um schema com os cinco tipos compostos de uma vez e confirma
       que cada um aparece com `marker="avro-type-badge"` e o texto
       correto, enquanto o campo primitivo (`long`) aparece só com
       `marker="avro-type-label"` — prova de ponta a ponta de que a tela
       usa o componente compartilhado, não uma formatação própria.

Nenhuma alteração foi necessária em `avro/schema_loader.py` (TASK-024)
nem em `services/kafka_service.py` (TASK-022) — o componente só consome
a string `tipo` já pronta.

## Definition of Done — verificação

- [x] O componente exibe corretamente os cinco tipos compostos suportados
      (FR-010) — `test_the_five_composite_types_are_rendered_via_the_shared_component`
      cobre union opcional, enum, array, map e record de ponta a ponta
      (upload → validação → renderização), complementado pelos testes
      unitários de `_badge_color` para cada categoria.
- [x] O mesmo componente é reutilizado sem duplicação de lógica de
      formatação entre páginas — hoje só `schemas_avro.py` mostra campos
      de schema e já usa `avro_type.render`; a lógica de *como* exibir um
      tipo composto existe em um único lugar (`app/ui/components/avro_type.py`),
      pronta para qualquer tela futura que precise do mesmo (ex.: o
      formulário auto-gerado de FR-012, ainda não implementado) sem
      reescrever essa decisão.

## Checklist

- [x] Unit tests pass — suíte completa: `194 passed` (185 anteriores + 8
      novos testes de `tests/test_avro_type_component.py` + 1 novo teste
      de página, com 1 teste existente ajustado para a nova estrutura de
      elementos; ambiente virtual criado temporariamente para rodar
      `pytest`, removido ao final).
- [x] Integration tests pass — cobertos pelo teste de página via fixture
      `user` do NiceGUI, exercitando upload → `services/kafka_service.py`
      → `avro/schema_loader.py` → `ui/components/avro_type.py` de ponta a
      ponta.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
