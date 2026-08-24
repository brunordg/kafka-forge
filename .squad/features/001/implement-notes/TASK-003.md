---
task: TASK-003
story: N/A (tarefa de infraestrutura)
status: done
---

# TASK-003 — `Dockerfile` e `docker-compose.yml`

## O que foi feito

Preenchidos `Dockerfile` e `docker-compose.yml` (criados vazios na
TASK-001) conforme a seção 10.4 do `plan.md`: empacotamento da aplicação
KafkaForge, subindo por padrão apenas o serviço da aplicação, com
Kafka/Schema Registry locais disponíveis como serviços opcionais via
profile do Docker Compose. Adicionado também `.dockerignore`, seguindo a
convenção de que a existência de um `Dockerfile` implica um `.dockerignore`
correspondente para não enviar `.squad/`, `.claude/`, `tests/` etc. no
contexto de build.

### `Dockerfile`

- Base `python:3.12-slim` (Python 3.12+, conforme seção 1 do `plan.md`).
- Instala `requirements.txt` (TASK-002) antes de copiar o código-fonte,
  para aproveitar cache de camada do Docker.
- Copia o conteúdo de `app/` diretamente para `/app` na imagem.
- `EXPOSE 8080` — porta padrão do NiceGUI, que `app/main.py` (TASK-004)
  usará para servir tanto as páginas NiceGUI quanto as rotas FastAPI no
  mesmo processo.
- Executa como usuário não-root (`kafkaforge`, uid 1000) em vez de root,
  como prática mínima de segurança do container.
- `CMD ["python", "main.py"]` — a aplicação sobe com um único comando,
  reforçando NFR-005; a lógica de bootstrap propriamente dita é
  implementada na TASK-004.

### `docker-compose.yml`

- Serviço `app`: builda a imagem a partir do `Dockerfile` local e publica a
  porta apenas em `127.0.0.1` do host (`127.0.0.1:${APP_PORT:-8080}:8080`),
  na mesma linha da decisão Q3 (seção 7 do plano) de que o serviço fica
  acessível somente pela máquina do desenvolvedor. Um volume nomeado
  (`kafkaforge-data`) é montado em `/home/kafkaforge/.kafkaforge` para
  persistir configurações/schemas/logs entre reinícios do container
  (armazenamento local da seção 9 do plano, implementado na TASK-006).
- Serviços `kafka` (`confluentinc/cp-kafka`, modo KRaft de nó único) e
  `schema-registry` (`confluentinc/cp-schema-registry`): marcados com
  `profiles: [local-infra]`, portanto **não** sobem com `docker-compose up`
  simples — só com `docker-compose --profile local-infra up`. Servem
  exclusivamente para desenvolvimento/teste local, nunca para uso contra o
  Kafka corporativo real (que é sempre configurado via Configuração de
  Ambiente na própria ferramenta).

## Verificação

- `docker compose config --services` → retorna apenas `app` (comportamento
  padrão do `docker-compose up`).
- `docker compose --profile local-infra config --services` → retorna
  `app`, `kafka` e `schema-registry`, confirmando que o profile ativa os
  serviços opcionais.
- `docker build` da imagem concluído com sucesso (dependências do
  `requirements.txt` instaladas via wheels pré-compilados, sem exigir
  toolchain de build).
- `docker inspect` da imagem construída confirma
  `ExposedPorts: {"8080/tcp": {}}` e `User: kafkaforge` (execução não-root).
- Imagem de teste removida (`docker rmi`) após a validação, sem deixar
  artefatos no ambiente.

## Checklist

- [ ] Unit tests pass — N/A, nenhum código de aplicação foi escrito nesta tarefa
- [ ] Integration tests pass — N/A, idem (a validação de integração real do
      profile `local-infra` fica para a TASK-060)
- [ ] Typecheck passes — N/A, idem
- [ ] Linter passes — N/A, idem

## Próximos passos

TASK-004 (`app/main.py` como bootstrap único do processo, bind exclusivo
em `127.0.0.1`, `docs_url="/docs"`), que dará conteúdo real ao `CMD` desta
imagem.
