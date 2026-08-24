---
task: TASK-006
story: N/A (tarefa de infraestrutura, pré-requisito de US-001a e US-007b)
status: done
---

# TASK-006 — Estrutura de armazenamento local (`~/.kafkaforge/`)

## O que foi feito

Criado `app/config/storage.py` com a estrutura de armazenamento local
descrita na seção 9 do `plan.md`, e conectado o bootstrap ao processo em
`app/main.py` para que a estrutura seja criada automaticamente na
primeira execução (exigência explícita da Definition of Done). Também
foi necessário corrigir uma inconsistência de layout entre `Dockerfile`
(TASK-003) e a convenção de import já validada pelos testes (TASK-005),
revelada apenas agora que `main.py` passou a ter seu primeiro import
interno do próprio pacote `app`.

### `app/config/storage.py` (novo)

- `get_base_dir()`: lê a variável de ambiente `KAFKAFORGE_HOME`; se
  ausente, usa `Path.home() / ".kafkaforge"` como padrão.
- `ensure_storage_structure()`: cria (se ainda não existirem) o diretório
  base, `schemas/`, `logs/` e `configurations.json` (inicializado como
  `"[]"`, uma lista JSON vazia de Configurações de Ambiente para a
  TASK-008 popular). Aplica permissões restritas ao dono do processo via
  `os.chmod` explícito após a criação — `0700` para diretórios, `0600`
  para `configurations.json` — em vez de confiar no modo passado a
  `mkdir()`/`open()`, que fica sujeito ao `umask` do processo e não é
  garantido.
- Operação idempotente: chamadas repetidas não recriam nem truncam
  `configurations.json` já existente (usa `if not path.exists()` antes de
  escrever), só reforça as permissões a cada chamada.
- Sem nenhuma dependência de `ui/`, `api/`, `kafka/`, `avro/` ou
  `registry/` — confirmado via `grep`.

### `app/main.py` (estendido)

Adicionada a chamada `ensure_storage_structure()` no nível do módulo,
antes da criação do `FastAPI(...)`, para que a estrutura de armazenamento
já exista assim que o processo sobe — tanto na primeira execução direta
quanto no worker de reload do NiceGUI (`__mp_main__`), já que a chamada é
idempotente e barata.

### `.env.example` (preenchido)

Documentada `KAFKAFORGE_HOME` (caminho base configurável, conforme
exigido pela DoD desta tarefa) e, por completude — já que o arquivo
estava vazio e essa variável já era usada desde a TASK-003/TASK-004 sem
nunca ter sido documentada —, também `APP_PORT`.

### Correção necessária em `Dockerfile` (TASK-003)

Ao ligar `ensure_storage_structure()` em `main.py`, o primeiro import
interno do pacote `app` (`from app.config.storage import
ensure_storage_structure`) expôs uma inconsistência latente: os testes da
TASK-005 já importam módulos como `from app.exceptions import ...`,
tratando `app` como pacote enraizado na raiz do repositório (via
`pyproject.toml` → `pythonpath = ["."]"`), enquanto o `Dockerfile` da
TASK-003 "achatava" o conteúdo de `app/` direto em `/app` no container
(`COPY app/ .`) e rodava `CMD ["python", "main.py"]` — um layout de script
solto, sem o pacote `app` visível. Isso nunca tinha quebrado porque
`main.py`, até a TASK-004, só importava bibliotecas externas.

Corrigido preservando o pacote `app/` dentro do container e executando
via módulo, alinhado à mesma convenção já usada pelos testes:

```dockerfile
WORKDIR /srv/kafkaforge
...
COPY app/ ./app/
...
CMD ["python", "-m", "app.main"]
```

Isso substitui o `WORKDIR /app` + `COPY app/ .` + `CMD ["python",
"main.py"]` anteriores. Optei por essa correção (em vez de reescrever os
imports para o estilo "flat" e alterar `pyproject.toml`/os testes já
validados da TASK-005) por ser o menor diff e o layout mais idiomático
para um projeto Python com pacote `app/` + `tests/` na raiz.

## Verificação

- `pytest -v` (venv limpo): 22 testes, todos `PASSED` (17 da TASK-005 +
  5 novos em `tests/test_storage.py`, cobrindo default de
  `get_base_dir()`, override via `KAFKAFORGE_HOME`, criação da árvore
  ausente, permissões `0700`/`0600` e idempotência preservando conteúdo
  existente).
- Execução real local via `python -m app.main` (a mesma forma que o
  `Dockerfile` agora usa), com `KAFKAFORGE_HOME` apontando para um
  diretório temporário isolado (sem tocar o `$HOME` real da máquina):
  - Estrutura criada: `.kafkaforge/`, `.kafkaforge/schemas/`,
    `.kafkaforge/logs/`, `.kafkaforge/configurations.json` (conteúdo
    `"[]"`).
  - Permissões confirmadas via `stat -c "%a"`: `700` nos três
    diretórios, `600` no arquivo.
  - `GET /` e `GET /docs` continuam respondendo HTTP 200 (bootstrap da
    TASK-004 não foi afetado pela mudança).
  - Bind confirmado exclusivamente em `127.0.0.1` via `ss -ltnp`.
- Rebuild da imagem Docker com o `Dockerfile` corrigido: build concluído
  com sucesso; dentro do container, a estrutura é criada no caminho
  padrão (`/home/kafkaforge/.kafkaforge`, o mesmo caminho já montado como
  volume nomeado desde a TASK-003), com as mesmas permissões `700`/`600`
  confirmadas via `docker exec ... stat`. `curl` do host para `/` e
  `/docs` continua retornando HTTP 000 — limitação já documentada na
  TASK-004 (bind em `127.0.0.1` é o loopback do próprio container), não
  uma regressão desta tarefa.
- Todos os processos, imagens e diretórios temporários de teste foram
  removidos ao final.

## Checklist

- [x] Unit tests pass — 22/22 testes (`tests/test_exceptions.py` +
      `tests/test_storage.py`)
- [ ] Integration tests pass — N/A, módulo não depende de nenhum sistema externo
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-007 (`app/config/models.py`) e TASK-008 (`app/config/manager.py`),
que devem usar `get_base_dir()`/`ensure_storage_structure()` deste módulo
para ler e escrever `configurations.json` de fato.
