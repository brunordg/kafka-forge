---
task: TASK-008
story: N/A (fundação; pré-requisito direto de US-001a e US-006)
status: done
---

# TASK-008 — `app/config/manager.py`

## O que foi feito

Criado `app/config/manager.py` com o CRUD completo de Configurações de
Ambiente sobre `configurations.json` (armazenamento local da TASK-006),
usando o modelo `EnvironmentConfiguration` da TASK-007. Cada configuração
é identificada pelo campo `nome`, e a unicidade desse nome é um invariante
mantido em toda operação de escrita — não só na criação.

```python
def list_configurations() -> list[EnvironmentConfiguration]: ...
def get_configuration(nome: str) -> EnvironmentConfiguration: ...
def create_configuration(configuration: EnvironmentConfiguration) -> EnvironmentConfiguration: ...
def update_configuration(nome: str, configuration: EnvironmentConfiguration) -> EnvironmentConfiguration: ...
def delete_configuration(nome: str) -> None: ...
```

Decisões de implementação:

- **Duas novas exceções em `app/exceptions.py`**:
  `ConfigurationAlreadyExistsError` e `ConfigurationNotFoundError`, ambas
  herdando de `KafkaForgeError` (TASK-005). Nenhuma das oito exceções
  originais da seção 8 do plano cobre "nome duplicado" ou "configuração
  inexistente"; em vez de usar `ValueError` solto dentro de
  `config/manager.py`, mantive a mesma regra arquitetural já estabelecida
  — toda exceção de domínio com mensagem amigável + detalhe técnico vive
  em `app/exceptions.py`, para que UI, API e o futuro Registro de Operação
  (TASK-010) consigam tratá-las de forma uniforme (FR-026).
- **`create_configuration` rejeita nome já existente** sem alterar o
  arquivo (`_read_all()` só é persistido de volta via `_write_all()` após
  a checagem de duplicidade passar) — satisfaz diretamente a DoD "a
  segunda tentativa é rejeitada com erro claro" e "sem sobrescrever
  silenciosamente" (também citado como DoD futura da TASK-013).
- **`update_configuration(nome, configuration)`** localiza o registro
  pelo `nome` atual (chave de busca) e grava o novo conteúdo; se o novo
  `configuration.nome` for diferente (renomeação) e colidir com outra
  configuração já existente, a operação é rejeitada com
  `ConfigurationAlreadyExistsError` sem tocar no arquivo — o invariante de
  unicidade vale para qualquer escrita, não só para `create`.
- **Leitura sempre feita do arquivo (`_read_all()`), sem cache em
  memória.** Cada chamada ao manager reflete o estado mais recente do
  `configurations.json`, o que também é a base para a leitura por
  snapshot exigida da TASK-009 (`services/kafka_service.py` não deve
  segurar uma referência mutável compartilhada entre chamadas).
- **`configuration.model_dump(mode="json")`** ao persistir: grava sempre
  a representação já validada pelo Pydantic (TASK-007), nunca um dict
  arbitrário passado pelo chamador.

## Verificação

- `tests/test_config_manager.py` (novo), 12 casos, incluindo diretamente
  os três itens da Definition of Done:
  - **Criar/listar/editar/remover funcionam via chamada direta ao
    módulo**: `test_create_and_list_configuration`,
    `test_create_and_get_configuration`,
    `test_update_configuration_changes_only_target_entry`,
    `test_delete_configuration_removes_only_target_entry`.
  - **Nomes duplicados são rejeitados com erro claro, sem sobrescrever**:
    `test_create_duplicate_name_is_rejected`,
    `test_create_duplicate_name_does_not_overwrite_existing_entry`,
    `test_update_renaming_to_existing_name_is_rejected`.
  - **Editar uma configuração não afeta as demais**:
    `test_update_configuration_changes_only_target_entry` cria três
    configurações, edita só a do meio e confirma que as outras duas
    permanecem com seus valores originais.
  - Casos adicionais de erro (`ConfigurationNotFoundError`) para
    `get`/`update`/`delete` sobre nomes inexistentes, e renomeação para um
    nome livre (`test_update_can_rename_to_a_free_name`).
  - Isolamento de storage por teste via fixture `autouse` que aponta
    `KAFKAFORGE_HOME` para um `tmp_path` novo a cada teste (mesmo padrão
    de `tests/test_storage.py`), sem tocar no `$HOME` real da máquina.
- `pytest -v` (venv limpo): **45 testes, todos `PASSED`** (12 novos em
  `tests/test_config_manager.py` + 33 já existentes das
  TASK-005/006/007 — nenhuma regressão).
- `grep` confirma que `app/config/manager.py` não importa nada de `ui`,
  `api`, `kafka`, `avro` ou `registry`.
- Ambiente virtual de teste e caches removidos após a validação.

## Checklist

- [x] Unit tests pass — 45/45 (12 novos em `tests/test_config_manager.py`)
- [ ] Integration tests pass — N/A, módulo só depende do sistema de arquivos local
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-009 (esqueleto de `services/kafka_service.py`, ponto único de
orquestração que deve consumir este manager por snapshot) e TASK-012/
TASK-013 (`api/schemas/configurations.py` e `api/routes/configurations.py`),
que expõem este CRUD via HTTP reaproveitando as mesmas exceções
`ConfigurationAlreadyExistsError`/`ConfigurationNotFoundError` introduzidas
aqui.
