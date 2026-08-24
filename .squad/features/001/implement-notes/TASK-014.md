---
task: TASK-014
story: US-001a
status: done
---

# TASK-014 — `app/ui/pages/configuracoes_kafka.py`

## O que foi feito

Criada a primeira página NiceGUI do projeto: `app/ui/pages/configuracoes_kafka.py`,
com formulário de criação/edição de Configuração de Ambiente (bloco Kafka
+ nome; o bloco `schema_registry` fica para a página própria da TASK-047,
US-005a) e lista das configurações salvas. Como esta é a primeira tarefa
de UI da feature, também foi necessário montar do zero a infraestrutura
de teste automatizado de páginas NiceGUI — inexistente até agora — e,
nesse processo, corrigir uma incompatibilidade real entre essa nova
infraestrutura e os testes de API já existentes (detalhado abaixo).

### `app/ui/pages/configuracoes_kafka.py` (novo)

Rota `/configuracoes/kafka`. Estrutura:

- Formulário com `nome`, `bootstrap_servers`, `security_protocol` (select),
  `sasl_mechanism` (select, só `PLAIN` ou "nenhum"), `username`, `password`,
  `client_key_password`, e três `ui.upload` para `ca_cert`/`client_cert`/
  `client_key` (FR-003) — o conteúdo do arquivo é lido como texto e guardado
  em memória (estado local da conexão do cliente) até o "Salvar".
- Lista de configurações salvas (nome + `bootstrap_servers`), cada uma com
  um botão "Editar" que repreenche o formulário inteiro com os dados
  daquela configuração.
- Botão "Nova configuração" para limpar o formulário.
- Todas as chamadas de leitura/escrita passam por `services/kafka_service.py`
  (`list_configurations`, `create_configuration`, e o novo
  `update_configuration` — ver abaixo), nunca por `config/manager.py`
  diretamente — confirmado pelo guarda-corrim arquitetural já existente
  (TASK-009/TASK-013), que agora também cobre este arquivo real.
- Estado por conexão de cliente vive inteiramente na closure da função da
  página (`state`, `existing_schema_registry`), nunca em variável de
  módulo — cada aba/desenvolvedor que abre a página tem seu próprio
  estado de edição, sem interferência cruzada.
- **Editar preserva o `schema_registry` existente**: como este formulário
  só edita o bloco Kafka, salvar uma edição carrega adiante o
  `schema_registry` que já estava na configuração (guardado em
  `existing_schema_registry` ao clicar "Editar"), em vez de sobrescrevê-lo
  com `None` — do contrário, editar os dados de Kafka de uma configuração
  apagaria silenciosamente o Schema Registry já configurado para ela pela
  tela da TASK-047.

### `app/services/kafka_service.py` (estendido)

Adicionado `update_configuration(nome_atual, configuration)` (passthrough
para `config_manager.update_configuration`), necessário para que o
"formulário de edição" desta tarefa realmente funcione — sem ele, salvar
uma configuração já existente teria caído no `create_configuration` e
sido rejeitado com `ConfigurationAlreadyExistsError`. Não foi criada
nenhuma rota HTTP de atualização: a UI chama `kafka_service` diretamente
como função Python (mesmo processo, arquitetura da seção 3.1 do plano —
"`ui/` e `api/` chamam exclusivamente `services/kafka_service.py`"), sem
precisar de um endpoint REST para isso. (A ação "Remover" — e sua rota
`DELETE`, TASK-013b — ficou de fora desta tarefa: `TASK-014b`, que
apareceu em `tasks.md` durante esta sessão fechando um achado do
`analysis.md`, é quem cobre isso.)

## Infraestrutura de teste de UI (nova, necessária para esta tarefa)

Não existia nenhum jeito de testar páginas NiceGUI automaticamente até
agora. Investiguei e usei o fixture `user` embutido em
`nicegui.testing.user_plugin` (simulação sem navegador real, via
`httpx.AsyncClient` contra o app interno do NiceGUI) em vez de
`nicegui.testing.screen` (que exige Selenium/navegador real — dependência
pesada e desnecessária para uma ferramenta local de desenvolvimento).

- **`conftest.py`** (novo, raiz do projeto): `pytest_plugins =
  ["nicegui.testing.user_plugin"]` — registra só o fixture `user`
  (sem depender de `nicegui.testing.plugin`, que importa Selenium).
- **`pyproject.toml`**: adicionadas `main_file = "app/main.py"` (ini
  option do plugin acima, aponta para o arquivo que o fixture `user`
  re-executa via `runpy` a cada teste) e `asyncio_mode = "auto"` (os
  testes de UI são `async def`, precisam de `pytest-asyncio`).
- **`requirements-dev.txt`**: adicionado `pytest-asyncio==1.4.0`.
- **`app/main.py`**: adicionado o guard `not is_pytest()` (de
  `nicegui.helpers`) antes de `uvicorn.run(...)`. Sem isso, o fixture
  `user` (que executa `app/main.py` de verdade via `runpy.run_path(...,
  run_name="__main__")`) travaria a suíte inteira tentando subir um
  servidor Uvicorn bloqueante dentro do processo de teste. Este é
  exatamente o padrão que o próprio `ui.run()` do NiceGUI usa
  internamente — só precisei replicá-lo porque `app/main.py` chama
  `uvicorn.run()` manualmente (arquitetura "integrar com FastAPI" da
  TASK-004).
- **`app/ui/pages/__init__.py`** (novo): agregador que importa
  `configuracoes_kafka` pelo efeito colateral do `@ui.page(...)`,
  registrado em `app/main.py` com um único `import app.ui.pages` — mesmo
  padrão de ponto único de inclusão já usado para `api/routes/`
  (TASK-011), para que tarefas futuras (TASK-023, TASK-030, TASK-042,
  TASK-047, TASK-050, TASK-054, TASK-056) só precisem adicionar um import
  aqui, nunca mexer em `main.py` de novo.

### Conflito real encontrado e corrigido: `tests/conftest.py`

Ao rodar a suíte inteira (não só os testes novos), testes que já
passavam (`test_health_route.py`, `test_configurations_route.py`)
começaram a falhar de forma dependente da ordem dos arquivos. Causa raiz:
`core.app` — o registro interno de páginas do NiceGUI, que nosso `app`
monta via `ui.run_with()` (TASK-004) — é um **singleton de todo o
processo**. O fixture `user` reseta e reconstrói `core.app` a cada teste
(via `nicegui_reset_globals()`, inclusive purgando `app.main` de
`sys.modules`); os testes antigos importavam `app.main` **uma única vez**
no topo do arquivo e reaproveitavam esse `app`/`TestClient` para todos os
testes daquele arquivo. Depois que qualquer teste de UI rodava, o
`core.app` ficava resetado sem a configuração que `ui.run_with()` aplica
(`core.app.config` sem o atributo `markdown`, por exemplo), quebrando até
respostas 404 simples nos testes de API que rodassem depois.

Corrigido consolidando em **`tests/conftest.py`** (novo):
- `isolated_storage` (fixture `autouse`, movida para cá de 5 arquivos que
  a duplicavam: `test_config_manager.py`, `test_operation_log.py`,
  `test_kafka_service.py`, `test_configurations_route.py` e
  `test_configuracoes_kafka_page.py`).
- **`api_client`** (novo): em vez de um `TestClient` importado uma vez no
  topo do arquivo, este fixture reconstrói `app/main.py` do zero a cada
  teste com a mesma disciplina de `nicegui_reset_globals()` usada pelo
  fixture `user` — eliminando a dependência de ordem por completo.
  `test_health_route.py` e `test_configurations_route.py` foram
  atualizados para receber `api_client` como parâmetro em vez de usar um
  `client` de nível de módulo.

Validado explicitamente rodando a suíte em ambas as ordens (arquivos de
API antes dos de UI, e o inverso) — 18/18 testes relevantes passam nos
dois sentidos, e a suíte completa (108 testes) passa tanto na ordem
padrão do pytest quanto forçando as duas ordens opostas.

## Verificação

- **`tests/test_configuracoes_kafka_page.py`** (novo), 6 casos usando o
  fixture `user` (interação simulada: digitar em campos via `.type()`,
  clicar botões via `.click()`, simular upload via
  `upload_element.handle_uploads([...])` — hook oficial documentado no
  próprio código-fonte do NiceGUI "for simulating file uploads in
  tests"), cobrindo as três exigências da Definition of Done:
  - **Preencher e salvar sem nenhuma configuração prévia (cenário 1)**:
    `test_developer_with_no_saved_configuration_can_fill_and_save`.
  - **Aparece na lista e pode ser reaberta para edição**:
    `test_saved_configuration_appears_in_the_list` +
    `test_saved_configuration_can_be_reopened_for_editing` (limpa o
    formulário antes de clicar "Editar", provando que o repreenchimento
    é real, não coincidência de estado nunca alterado) +
    `test_editing_and_saving_updates_the_existing_configuration_in_place`
    (a edição realmente persiste, sem duplicar registro).
  - **Upload de certificado funciona (FR-003)**:
    `test_certificate_upload_is_stored_and_persisted_on_save` — simula o
    upload de um certificado, confirma a notificação de "carregado" e
    confirma que o conteúdo do arquivo foi persistido em
    `configurations.json` depois do "Salvar".
  - Bônus: `test_creating_a_duplicate_name_shows_a_clear_error_without_overwriting`,
    replicando na UI a mesma garantia já testada na API (TASK-013).
- `pytest -v` (venv limpo, instalado só a partir de
  `requirements-dev.txt`): **108 testes, todos `PASSED`** (6 novos de UI +
  102 já existentes — sem regressão, depois da correção do conflito de
  `core.app` acima).
- `grep` confirma que `app/ui/pages/configuracoes_kafka.py` não importa
  nada de `kafka`, `avro`, `registry` nem `config.manager`.
- **Execução real de ponta a ponta** via `python -m app.main` (deps de
  produção) + `curl`: `GET /configuracoes/kafka` → HTTP 200, contém
  "Configurações — Kafka", "Nome da configuração" e os três widgets de
  upload; `/docs` continua respondendo 200; bind continua exclusivo em
  `127.0.0.1` (TASK-004 intacto). Processo e todos os ambientes/arquivos
  temporários removidos ao final.

## Checklist

- [x] Unit tests pass — 108/108 (6 novos em `test_configuracoes_kafka_page.py`)
- [ ] Integration tests pass — N/A, verificado via execução real de ponta a ponta (ver seção "Verificação")
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-014b (ação "Remover" na lista, com confirmação, usando `DELETE
/api/v1/configurations/{name}` da TASK-013b) e TASK-015 (`app/kafka/connection.py`,
início de US-001b). A infraestrutura de teste de UI criada aqui
(`conftest.py`, fixture `user`, `api_client`, `app/ui/pages/__init__.py`)
já fica disponível para todas as páginas seguintes.
