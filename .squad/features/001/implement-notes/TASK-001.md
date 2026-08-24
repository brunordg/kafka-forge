---
task: TASK-001
story: N/A (tarefa de infraestrutura, base para todas as stories)
status: done
---

# TASK-001 — Estrutura de diretórios do projeto

## O que foi feito

Criada a estrutura de diretórios e os arquivos-placeholder do KafkaForge
conforme a seção 3.2 do `plan.md`, sem nenhuma lógica de negócio (esta
tarefa é puramente estrutural — a implementação de cada módulo é objeto
das tarefas seguintes, TASK-002 em diante).

### Diretórios criados

```text
app/ui/pages/
app/ui/components/
app/api/routes/
app/api/schemas/
app/kafka/
app/avro/
app/registry/
app/config/
app/services/
tests/
```

Diretórios que ainda não possuem nenhum arquivo de código receberam um
`.gitkeep` (mesma convenção já usada em `.squad/agents/`, `.squad/kb/`,
`.squad/templates/` e `.squad/features/001/stories/`), garantindo que a
estrutura fique versionável assim que o repositório Git for inicializado.

### Arquivos criados

| Arquivo | Conteúdo |
|---|---|
| `app/main.py` | vazio — bootstrap real entra na TASK-004 |
| `Dockerfile` | vazio — conteúdo real entra na TASK-003 |
| `docker-compose.yml` | vazio — conteúdo real entra na TASK-003 |
| `requirements.txt` | vazio — dependências fixadas entram na TASK-002 |
| `README.md` | apenas título `# KafkaForge` — conteúdo completo entra na TASK-062 |
| `.env.example` | vazio — variáveis de ambiente entram na TASK-006 (armazenamento local) e demais tarefas relacionadas |

## Verificação

A árvore final foi conferida diretório a diretório contra a seção 3.2 do
`plan.md` e corresponde exatamente ao esperado.

## Checklist

- [ ] Unit tests pass — N/A, nenhum código com lógica foi escrito nesta tarefa
- [ ] Integration tests pass — N/A, idem
- [ ] Typecheck passes — N/A, idem
- [ ] Linter passes — N/A, idem

## Próximos passos

Sequência natural: TASK-002 (`requirements.txt` com dependências fixadas),
TASK-003 (`Dockerfile`/`docker-compose.yml`), TASK-004 (`app/main.py`
como bootstrap único do processo), TASK-005 (`app/exceptions.py`) e
TASK-006 (armazenamento local em `~/.kafkaforge/`).
