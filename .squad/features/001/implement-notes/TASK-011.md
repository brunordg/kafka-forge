---
task: TASK-011
story: N/A (fundação; pré-requisito direto de US-004a)
status: done
---

# TASK-011 — `GET /api/v1/health` e o agregador de rotas

## O que foi feito

Criados `app/api/schemas/health.py`, `app/api/routes/health.py` e
`app/api/routes/__init__.py` (agregador de rotas), e `app/main.py`
estendido com o único ponto de `app.include_router(...)` previsto na
arquitetura (seção 6.1 do plano). **Esta tarefa fecha a Fase 2 —
Fundação.**

```python
# app/api/schemas/health.py
class HealthStatus(BaseModel):
    status: str


# app/api/routes/health.py
router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthStatus)
def get_health() -> HealthStatus:
    return HealthStatus(status="ok")


# app/api/routes/__init__.py
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
```

```python
# app/main.py — único trecho adicionado
from app.api.routes import api_router
...
app.include_router(api_router)
```

Decisões de implementação:

- **`app/api/routes/__init__.py` como agregador único.** Em vez de
  `main.py` chamar `include_router` uma vez por módulo de rota, cada novo
  arquivo em `api/routes/` (TASK-013 `configurations.py`, TASK-022
  `schema.py`, TASK-029/TASK-035 `messages.py`) se registra dentro deste
  `__init__.py`, nunca em `main.py`. Isso é literalmente a terceira linha
  da Definition of Done: "novas rotas podem ser registradas em
  `api/routes/` sem alterar `main.py` além de um único ponto de inclusão
  de router" — e esse ponto único já existe agora, então tarefas futuras
  não precisam tocar em `main.py` de novo.
- **Prefixo `/api/v1` centralizado no agregador**, não em cada router
  individual. `health.py` declara só a rota `/health`; o prefixo vem de
  `APIRouter(prefix="/api/v1")` em `__init__.py`. Assim, se o versionamento
  da API mudar no futuro, é um ponto só de alteração.
- **`app/api/schemas/health.py` com `HealthStatus` (Pydantic)**, em vez de
  a rota devolver um `dict` solto. Já deixa a rota com `response_model`
  definido desde já — a mesma exigência que a TASK-041 vai revisar em
  todas as rotas mais tarde ("todas as rotas... têm `response_model`
  definido... para que a documentação em `/docs` seja gerada
  automaticamente sem manutenção manual", FR-022) — e mantém a convenção
  do plano de que `api/schemas/` guarda os contratos HTTP.

## Verificação

- **`tests/test_health_route.py`** (novo), usando
  `fastapi.testclient.TestClient` sobre o `app` real de `app/main.py`:
  - `GET /api/v1/health` → 200, `{"status": "ok"}`.
  - `GET /health` (sem o prefixo) → 404, confirmando que o prefixo
    `/api/v1` está de fato sendo aplicado pelo agregador, não hardcoded
    dentro de `health.py`.
  - `/openapi.json` contém `/api/v1/health` com o método `get` — prova
    de que a rota "aparece automaticamente em `/docs`" (segundo item da
    DoD) assim que `main.py` monta o FastAPI, sem nenhum passo manual de
    documentação.
  - `GET /docs` → 200, contém `swagger-ui`.
  - Um teste de guarda-corrim lê o código-fonte de `app/main.py` e
    confirma que `.include_router(` aparece **exatamente uma vez** —
    verificação automatizada do terceiro item da DoD, no mesmo espírito
    do guarda-corrim já criado na TASK-009 para a fronteira `ui/`/`api/`.
  - **Cuidado de isolamento**: como este é o primeiro teste que importa
    `app.main` (e portanto dispara `ensure_storage_structure()` da
    TASK-006 no momento do import), o módulo define
    `KAFKAFORGE_HOME` para um diretório temporário via
    `os.environ.setdefault(...)` **antes** do `from app.main import app`
    — evitando que rodar a suíte de testes crie um `~/.kafkaforge` real na
    máquina de quem executa `pytest`. Os demais testes já isolados por
    `monkeypatch.setenv` (fixture `isolated_storage`) continuam
    funcionando normalmente, já que `monkeypatch` sempre restaura o valor
    anterior ao final de cada teste.
- `pytest -v` (venv limpo): **73 testes, todos `PASSED`** (5 novos em
  `test_health_route.py` + 68 já existentes das TASK-005 a TASK-010 —
  nenhuma regressão). Rodar com `-W error` gera um único aviso
  (`StarletteDeprecationWarning` sugerindo o pacote `httpx2` no lugar de
  `httpx` dentro do `TestClient`) — não relacionado a nenhum código desta
  tarefa, apenas uma migração recém-anunciada por uma dependência
  transitiva ainda não fixada em `requirements.txt`; sem impacto no
  funcionamento real, registrado aqui só para transparência.
- **Execução real de ponta a ponta** via `python -m app.main` (com
  `KAFKAFORGE_HOME` isolado): `GET /api/v1/health` → `{"status":"ok"}`;
  `GET /docs` → 200; `GET /openapi.json` lista exatamente
  `["/api/v1/health"]`; `ss -ltnp` confirma bind exclusivo em
  `127.0.0.1:8091` (bootstrap da TASK-004 intacto). Processo de teste
  encerrado e artefatos temporários removidos ao final.
- `grep` confirma que nada em `app/api/` importa `ui`, `kafka`, `avro` ou
  `registry`; `tests/test_architecture_boundaries.py` (TASK-009) também
  passa isoladamente.

## Checklist

- [x] Unit tests pass — 73/73 (5 novos em `tests/test_health_route.py`)
- [ ] Integration tests pass — N/A, verificado via execução real de ponta a ponta (ver seção "Verificação"), não há sistema externo envolvido
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

**Fase 2 — Fundação concluída.** Início da Fase 3 (User Stories P1) com a
TASK-012 (`app/api/schemas/configurations.py`), primeira tarefa da
US-001a.
