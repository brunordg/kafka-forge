# TASK-019 — Implementação

**Story**: US-001b
**Tela**: `app/ui/pages/configuracoes_kafka.py`

## O que mudou

1. **`app/ui/pages/configuracoes_kafka.py`**
   - Adicionado um botão "Testar conexão" (`mark(f"test-connection-button-{configuration.nome}")`)
     em cada linha da lista de configurações salvas, entre "Editar" e
     "Remover".
   - Novo handler `_make_test_connection_handler(nome)`, no mesmo padrão de
     fábrica de handler já usado por `_make_upload_handler`: retorna uma
     função assíncrona que:
     1. Mostra imediatamente `"Testando conexão com '{nome}'..."` em
        `status_label`, dando feedback visual enquanto o teste (até 10s,
        decisão Q2) está em andamento.
     2. Chama `kafka_service.test_connection(nome)` (implementado na
        TASK-017 — mesma função usada pela rota `POST
        /configurations/{name}/test` da TASK-018) através de
        `nicegui.run.io_bound`, para não bloquear o servidor NiceGUI
        durante a espera de rede.
     3. Em sucesso ou falha, substitui `status_label` pela `message` do
        `ConnectionTestResult`, com `text-positive`/`text-negative`
        conforme `result.success` — mesmo padrão visual já usado por
        `_save` e `_confirm_delete`.
     4. Trata `ConfigurationNotFoundError` (caso a configuração tenha sido
        removida por outra aba entre o clique e a resposta) com a mesma
        `friendly_message` da exceção.
   - Novo import: `from nicegui import events, run, ui` (adição de `run`
     para `run.io_bound`).

2. **Testes — `tests/test_configuracoes_kafka_page.py`**
   - Adicionado o dublê `_FakeAdminClient`/`_patch_admin_client` (mesma
     estratégia de `tests/test_kafka_service.py` e
     `tests/test_configurations_route.py`: nunca abre socket real, testes
     rápidos e determinísticos sem depender de um Kafka corporativo real —
     plano, seção 12).
   - `test_testing_a_valid_connection_shows_success_without_publishing_anything`
     (cenário 2 de US-001b na spec): clicar em "Testar conexão" com uma
     configuração válida mostra a mensagem de sucesso e comprova, via um
     `build_producer` monitorado, que nenhum `Producer` chega a ser
     construído (NFR-002).
   - `test_testing_an_invalid_connection_shows_an_understandable_failure`
     (cenário 3 de US-001b na spec): broker inacessível simulado mostra a
     mensagem de falha compreensível.
   - `test_connection_test_result_shown_in_the_ui_matches_the_api_response_shape`
     (NFR-006): monta a resposta esperada usando o mesmo contrato da API
     (`ConnectionTestResponse.from_domain`, TASK-018) e confirma que a
     mesma mensagem aparece na tela — prova de que UI e API exibem o
     resultado de forma equivalente, pois ambas chamam exclusivamente
     `kafka_service.test_connection`. Evita combinar os fixtures `user` e
     `api_client` no mesmo teste, devido ao aviso já documentado em
     `tests/conftest.py` sobre o singleton `core.app` do NiceGUI.

Nenhuma alteração foi necessária em `services/kafka_service.py`
(TASK-017) nem em `api/routes/configurations.py` (TASK-018) — a tela
apenas consome `test_connection`, já implementado.

## Definition of Done — verificação

- [x] Acionar "Testar conexão" com uma configuração válida exibe sucesso
      sem publicar nada — confirmado por
      `test_testing_a_valid_connection_shows_success_without_publishing_anything`.
- [x] Acionar "Testar conexão" com dado incorreto exibe falha com mensagem
      compreensível — confirmado por
      `test_testing_an_invalid_connection_shows_an_understandable_failure`.
- [x] O resultado exibido na UI é visualmente equivalente ao retornado
      pela API (TASK-018), preservando NFR-006 — confirmado por
      `test_connection_test_result_shown_in_the_ui_matches_the_api_response_shape`.

## Checklist

- [x] Unit tests pass — suíte completa: `154 passed` (151 anteriores + 3
      novos testes desta task; ambiente virtual criado temporariamente
      para rodar `pytest`, removido ao final).
- [x] Integration tests pass — cobertos pelos testes de página via fixture
      `user` do NiceGUI, que simulam clique real no botão "Testar
      conexão" sobre a pilha completa (página → `services/kafka_service.py`
      → `kafka/connection.py` → dublê de `AdminClient`, já que não há
      Kafka corporativo disponível neste ambiente).
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
