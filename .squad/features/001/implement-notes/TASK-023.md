# TASK-023 — Implementação

**Story**: US-002a
**Tela**: `app/ui/pages/schemas_avro.py` (novo, versão inicial)

## O que mudou

1. **`app/ui/pages/schemas_avro.py`** (novo arquivo)
   Nova página `@ui.page("/schemas/avro")`, seguindo o mesmo estilo de
   `configuracoes_kafka.py` (estado por conexão de cliente via closures,
   `ui.upload` com `auto_upload=True`, `status_label` com
   `text-positive`/`text-negative`):
   - Upload de `.avsc` (`mark("avsc-upload")`) lê o conteúdo do arquivo
     (`_read_upload_as_text`, mesmo helper já usado em
     `configuracoes_kafka.py` para certificados) e chama
     `kafka_service.validate_schema(content)` (TASK-022).
   - Em caso de schema válido: mostra `"Schema '{nome}' válido."` em
     `status_label`, preenche `Nome:`/`Namespace:` (com `(nenhum)` como
     placeholder quando não há namespace), lista os campos como
     `"{nome}: {tipo}"` em `schema-fields`, exibe o conteúdo original em
     um `ui.textarea` somente leitura (`schema-raw-content`) e torna a
     seção de detalhes visível.
   - Em caso de schema inválido: mostra `result.message` (a
     `friendly_message` de `AvroSchemaError`, via
     `kafka_service.validate_schema`) em `status_label` com
     `text-negative` e **oculta** a seção de detalhes
     (`details.visible = False`) — nenhuma exceção chega a escapar da
     página, e o widget de upload continua disponível para uma nova
     tentativa (FR-009: rejeição não interrompe o uso da tela).
   - Todas as referências (`status_label`, `details`, `nome_label`,
     `namespace_label`, `fields_list`, `raw_content_area`) são definidas
     antes de `_handle_upload`, e `_handle_upload` antes do `ui.upload(...)`
     que o registra — mesma ordem de definição (widgets → handler →
     widget-gatilho) já usada em `configuracoes_kafka.py`, sem
     referências antecipadas.

2. **`app/ui/pages/__init__.py`**
   Adicionado `from app.ui.pages import schemas_avro  # noqa: F401`, para
   que a página seja registrada quando `app/main.py` importa
   `app.ui.pages` (mesmo mecanismo já usado por `configuracoes_kafka`).

3. **Testes — `tests/test_schemas_avro_page.py`** (novo arquivo)
   5 casos com o fixture `user` do NiceGUI:
   - `test_uploading_a_valid_avsc_shows_name_namespace_fields_and_raw_content`
     (cenário 1): nome, namespace, campos com tipos e conteúdo original
     idêntico ao enviado.
   - `test_uploading_a_valid_avsc_without_namespace_shows_a_placeholder`:
     `namespace` ausente vira o placeholder `(nenhum)`.
   - `test_uploading_an_invalid_avsc_shows_an_understandable_explanation`
     (cenário 2/FR-009): JSON malformado mostra a mensagem compreensível
     de `AvroSchemaError`/`avro/schema_loader.py`, sem mostrar detalhes de
     um schema anterior.
   - `test_rejected_upload_does_not_prevent_a_subsequent_valid_upload`:
     depois de uma rejeição, um novo upload válido funciona normalmente
     na mesma tela (prova de que a rejeição "não interrompe o uso das
     demais telas").
   - `test_a_valid_upload_followed_by_an_invalid_one_hides_the_stale_details`:
     um upload inválido após um válido esconde os detalhes anteriores,
     evitando um estado confuso de "schema válido" desatualizado ao lado
     de uma mensagem de erro nova.

   Achado durante a implementação: os primeiros testes que verificavam
   `.text`/`.value` de um elemento logo após `handle_uploads(...)`, sem
   nenhum `await user.should_see(...)` entre as duas chamadas, falhavam
   de forma intermitente — o NiceGUI agenda o `on_upload` assíncrono como
   tarefa em segundo plano, e `handle_uploads` não espera essa tarefa
   terminar. A correção (já refletida nos testes finais) foi sempre fazer
   um `await user.should_see(...)` (que faz retries com espera
   assíncrona) antes de inspecionar atributos de elemento diretamente.

Nenhuma alteração foi necessária em `services/kafka_service.py`
(TASK-022) nem em `avro/schema_loader.py` (TASK-021) — a página só
consome `kafka_service.validate_schema`, já implementado.

## Definition of Done — verificação

- [x] Upload de um `.avsc` válido exibe nome, namespace, campos, tipos e
      conteúdo original (cenário 1) —
      `test_uploading_a_valid_avsc_shows_name_namespace_fields_and_raw_content`.
- [x] Upload de um `.avsc` inválido exibe explicação compreensível do
      problema, sem interromper o uso das demais telas (FR-009) —
      `test_uploading_an_invalid_avsc_shows_an_understandable_explanation`
      e `test_rejected_upload_does_not_prevent_a_subsequent_valid_upload`.

## Checklist

- [x] Unit tests pass — suíte completa: `180 passed` (175 anteriores + 5
      novos testes de `tests/test_schemas_avro_page.py`; ambiente virtual
      criado temporariamente para rodar `pytest`, removido ao final).
- [x] Integration tests pass — cobertos pelos testes de página via
      fixture `user` do NiceGUI, exercitando a pilha completa upload →
      página → `services/kafka_service.py` → `avro/schema_loader.py`.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
