# TASK-013b — Implementação

**Story**: US-001a
**Rota**: `DELETE /api/v1/configurations/{name}`

## O que mudou

1. **`app/services/kafka_service.py`**
   Adicionada a função `delete_configuration(nome: str) -> None`, seguindo o
   mesmo padrão de passthrough das demais operações de configuração
   (`list_configurations`, `create_configuration`, `update_configuration`):
   delega diretamente a `config_manager.delete_configuration` (TASK-008) e
   propaga `ConfigurationNotFoundError` quando o nome não existe. Nenhuma
   camada (`ui/`, `api/`) chama `config/manager.py` diretamente — regra de
   arquitetura reforçada por `tests/test_architecture_boundaries.py`.

2. **`app/api/routes/configurations.py`**
   Adicionada a rota `DELETE /{name}`, retornando `204 No Content` em caso
   de sucesso. Captura `ConfigurationNotFoundError` e converte para
   `404 Not Found`, com `detail` igual à `friendly_message` da exceção
   (mesmo padrão usado em `POST` para `ConfigurationAlreadyExistsError`).
   Import de `ConfigurationNotFoundError` adicionado ao topo do arquivo.

3. **Testes**
   - `tests/test_configurations_route.py`: adicionados
     `test_delete_configuration_removes_it_from_a_subsequent_get`,
     `test_delete_configuration_does_not_affect_the_others` e
     `test_delete_nonexistent_configuration_returns_404_with_an_understandable_message`;
     o teste de documentação OpenAPI passou a exigir também `delete` em
     `/api/v1/configurations/{name}`.
   - `tests/test_kafka_service.py`: adicionados
     `test_delete_configuration_delegates_to_config_manager`,
     `test_delete_configuration_does_not_affect_other_configurations` e
     `test_delete_configuration_propagates_configuration_not_found`.

`app/config/manager.py` já continha `delete_configuration` (TASK-008,
pré-existente) — nenhuma alteração necessária ali.

## Definition of Done — verificação

- [x] `DELETE /api/v1/configurations/{name}` remove a configuração; um `GET`
      subsequente não a lista mais.
- [x] Remover uma configuração inexistente retorna `404` com mensagem clara
      (`"Configuração 'Inexistente' não encontrada."`), sem afetar as demais
      configurações salvas.
- [x] A rota não chama `config/manager.py` diretamente — passa por
      `services/kafka_service.py` (mesma regra de TASK-013), verificado por
      `tests/test_architecture_boundaries.py`.

## Checklist

- [x] Unit tests pass — suíte completa: `139 passed` (ambiente virtual criado
      temporariamente para rodar `pytest`, pois o projeto não tinha um `.venv`
      com as dependências instaladas; removido ao final).
- [x] Integration tests pass — cobertos pelos testes de rota via
      `fastapi.testclient` (`api_client` fixture), que exercitam a pilha
      completa API → `services/` → `config/manager.py` → armazenamento local.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado (`pyproject.toml` só define `[tool.pytest.ini_options]`).
      Sanidade mínima verificada com `py_compile` nos arquivos alterados.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
