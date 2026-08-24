# TASK-014b — Implementação

**Story**: US-001a
**Tela**: `app/ui/pages/configuracoes_kafka.py`

## O que mudou

1. **`app/ui/pages/configuracoes_kafka.py`**
   - Adicionado um botão "Remover" (`mark(f"delete-button-{configuration.nome}")`)
     em cada linha da lista de configurações salvas, ao lado do botão
     "Editar" já existente.
   - Adicionado um diálogo de confirmação único (`ui.dialog()`), reaberto a
     cada clique em "Remover" com o nome da configuração pendente guardado
     em `delete_pending` (estado por conexão de cliente, mesmo padrão de
     `state`/`existing_schema_registry` já usado na página). O diálogo
     mostra "Remover a configuração '{nome}'?" e oferece "Cancelar"
     (`mark("cancel-delete-button")`, apenas fecha o diálogo sem chamar o
     serviço) e "Remover" (`mark("confirm-delete-button")`, executa a
     exclusão).
   - A confirmação chama `kafka_service.delete_configuration(nome)` — a
     mesma função de orquestração introduzida na TASK-013b, que por sua vez
     delega a `config/manager.py` — preservando a regra de que `ui/` nunca
     chama `config/manager.py` diretamente e que UI e API percorrem o mesmo
     caminho de código (NFR-006).
   - Após a exclusão bem-sucedida: mensagem de sucesso em `status_label`,
     recarga da lista via `_refresh_list()` (sem exigir reload manual da
     página) e, se a configuração removida era a que estava aberta no
     formulário de edição, o formulário é limpo (`_clear_form()`) para não
     deixar o desenvolvedor editando algo que não existe mais.
   - `ConfigurationNotFoundError` (propagada por `kafka_service`, caso a
     configuração já tenha sido removida por outra aba/cliente) é tratada
     com a mesma mensagem amigável exibida em `status_label`, seguindo o
     padrão já usado em `_save`.

2. **Testes — `tests/test_configuracoes_kafka_page.py`**
   Adicionados três testes com o fixture `user` do NiceGUI:
   - `test_removing_a_saved_configuration_requires_confirmation_before_deleting`:
     clicar em "Remover" abre a confirmação; clicar em "Cancelar" não
     remove nada.
   - `test_confirming_removal_deletes_the_configuration_without_a_manual_reload`:
     confirmar a remoção some a configuração da lista imediatamente e
     preserva as demais.
   - `test_removing_the_configuration_currently_open_in_the_form_clears_it`:
     remover a configuração que estava sendo editada limpa o formulário.

Nenhuma alteração foi necessária em `services/kafka_service.py` nem em
`config/manager.py` — ambos já continham `delete_configuration` desde a
TASK-013b/TASK-008.

## Definition of Done — verificação

- [x] Um desenvolvedor consegue remover uma configuração salva diretamente
      pela lista da tela (fecha a lacuna de FR-001, achado G1 de
      `analysis.md`).
- [x] A remoção pede confirmação antes de executar (diálogo com
      "Cancelar"/"Remover"), evitando exclusão acidental.
- [x] Após remover, a configuração some da lista sem recarregar a página
      manualmente (`_refresh_list()` reativo), com o mesmo comportamento da
      rota `DELETE /api/v1/configurations/{name}` (TASK-013b), pois ambas
      passam por `kafka_service.delete_configuration` (NFR-006).

## Checklist

- [x] Unit tests pass — suíte completa: `142 passed` (139 anteriores + 3
      novos testes desta task; ambiente virtual criado temporariamente para
      rodar `pytest`, removido ao final).
- [x] Integration tests pass — cobertos pelos testes de página via fixture
      `user` do NiceGUI, que simulam clique real nos botões da UI sobre a
      pilha completa (página → `services/` → `config/manager.py` →
      armazenamento local).
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
