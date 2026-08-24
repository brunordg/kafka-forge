---
task: TASK-004
story: N/A (tarefa de infraestrutura, pré-requisito de US-004b)
status: done
---

# TASK-004 — `app/main.py` como bootstrap único do processo

## O que foi feito

Implementado `app/main.py` (vazio desde a TASK-001) como ponto único de
entrada do processo KafkaForge, seguindo a arquitetura da seção 3.1 do
`plan.md`: uma única instância de `FastAPI` é criada, as páginas NiceGUI
são montadas nela via `ui.run_with(app)`, e o processo inteiro é servido
por um único `uvicorn.run(app, host="127.0.0.1", port=...)`.

```python
import os

import uvicorn
from fastapi import FastAPI
from nicegui import ui

APP_HOST = "127.0.0.1"
APP_PORT = int(os.environ.get("APP_PORT", "8080"))

app = FastAPI(title="KafkaForge", docs_url="/docs")


@ui.page("/")
def index() -> None:
    ui.label("KafkaForge")


ui.run_with(app)

if __name__ in {"__main__", "__mp_main__"}:
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
```

Decisões de implementação:

- **`APP_HOST` é uma constante fixa em `"127.0.0.1"`, não configurável por
  variável de ambiente.** Isso é proposital: a decisão Q3 (seção 7 do
  plano) rejeitou explicitamente permitir bind em `0.0.0.0`; deixar o host
  configurável reabriria essa porta de escape. Só `APP_PORT` é lido de
  `os.environ` (com default `8080`, coerente com `ENV APP_PORT=8080` do
  `Dockerfile` da TASK-003).
- **`ui.run_with(app)` em vez de `ui.run(...)`**: é o padrão oficial do
  NiceGUI para "montar o FastAPI no mesmo processo" em vez de deixar o
  NiceGUI subir seu próprio servidor Uvicorn interno — permite que
  `app` seja a mesma instância `FastAPI` usada por `api/routes/` (TASK-011
  em diante) e que `docs_url="/docs"` funcione como um FastAPI comum.
  `ui.run_with` apenas monta rotas/estáticos/websocket na instância dada;
  quem efetivamente sobe o processo é o `uvicorn.run(app, ...)` explícito
  logo abaixo.
- **Página `index()` em `"/"`** é um placeholder mínimo só para provar que
  a montagem de páginas NiceGUI funciona nesta base; as páginas reais
  (`ui/pages/dashboard.py`, etc.) chegam nas fases seguintes e devem
  substituir/complementar esta rota.
- **Nenhuma rota de `api/routes/` é incluída ainda** — o diretório está
  vazio até a TASK-011, que deve adicionar o único ponto de
  `app.include_router(...)` neste arquivo, sem tocar em mais nada aqui.

## Verificação

Executada em duas frentes:

1. **Execução local (fora do Docker)**, em um venv limpo com as
   dependências da TASK-002:
   - `python main.py` sobe com um único comando; log confirma
     `Uvicorn running on http://127.0.0.1:8080`.
   - `GET /` → HTTP 200, contém `KafkaForge` (página NiceGUI servida).
   - `GET /docs` → HTTP 200, contém `swagger-ui` (Swagger UI do FastAPI).
   - `GET /openapi.json` → schema OpenAPI válido (`paths: {}`, já que
     nenhuma rota de negócio existe ainda — será populado a partir da
     TASK-011).
   - `ss -ltnp` confirma que o processo escuta **apenas** em
     `127.0.0.1:8080`, nunca em `0.0.0.0:8080`.
   - Processo de teste encerrado e venv temporário removido ao final.

2. **Execução dentro do container Docker** (imagem da TASK-003, agora com
   `CMD ["python", "main.py"]` funcional):
   - `docker build` concluído com sucesso.
   - `docker run -p 127.0.0.1:18080:8080 ...` sobe o processo (log idêntico
     ao da execução local), mas `curl` do host para
     `http://127.0.0.1:18080/` e `/docs` **falha** (HTTP 000).
   - Container e imagem de teste removidos ao final.

### Observação importante (não é um defeito desta tarefa)

O bind em `127.0.0.1` dentro do container é o `127.0.0.1` do **namespace
de rede do próprio container**, não do host. Por isso, o mapeamento de
porta do `docker-compose.yml` (`127.0.0.1:${APP_PORT}:8080`, da TASK-003)
não consegue alcançar a aplicação de fora do container — é uma
consequência direta e esperada da decisão Q3, cumprida à risca conforme a
Definition of Done desta tarefa ("nenhuma tentativa de expor em
`0.0.0.0`"), e não algo que esta tarefa deveria corrigir. Registrado aqui
para visibilidade: se o empacotamento Docker do próprio KafkaForge (não
dos serviços opcionais `kafka`/`schema-registry`) precisar ser
efetivamente acessível a partir do host no futuro, isso exigiria uma
decisão explícita de arquitetura (por exemplo, `network_mode: host` em
Linux, fora do escopo desta feature), e não uma mudança silenciosa do
bind.

## Checklist

- [ ] Unit tests pass — N/A, nenhum teste automatizado foi criado nesta
      tarefa; verificação feita por execução manual ponta a ponta (ver
      seção "Verificação")
- [ ] Integration tests pass — N/A, idem
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de
      typecheck (fora do escopo desta tarefa)
- [ ] Linter passes — N/A, idem

## Próximos passos

TASK-005 (`app/exceptions.py`) e TASK-011 (rota `GET /api/v1/health` +
mecanismo de registro de rotas), que deve adicionar em `app/main.py` o
único ponto de `app.include_router(...)` mencionado acima.
