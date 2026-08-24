---
task: TASK-002
story: N/A (tarefa de infraestrutura)
status: done
---

# TASK-002 — `requirements.txt` com dependências fixadas

## O que foi feito

Preenchido `requirements.txt` (criado vazio na TASK-001) com as bibliotecas
Python definidas na seção 10.1 do `plan.md`, todas com versão fixada
(pinned), e documentados no `README.md` os pré-requisitos de sistema
operacional para o caso de `confluent-kafka`/`librdkafka` precisar ser
compilado a partir do código-fonte.

### `requirements.txt`

```text
nicegui==3.16.0
fastapi==0.141.1
uvicorn==0.52.4
confluent-kafka[schema-registry]==2.15.0
fastavro==1.12.2
pydantic==2.13.4
```

As versões foram obtidas das versões estáveis mais recentes disponíveis no
PyPI no momento da implementação (`pip index versions <pacote>`), sem
usar faixas (`>=`, `~=`), conforme exigido pela Definition of Done
("versões fixadas/pinned").

### `README.md`

Adicionada a seção "Pré-requisitos de sistema operacional", explicando que
`confluent-kafka` distribui wheels pré-compilados para as combinações mais
comuns de SO/arquitetura (então normalmente não é preciso compilar nada) e
listando o toolchain necessário caso o `pip` precise compilar a partir do
código-fonte: `build-essential`/`librdkafka-dev` (Debian/Ubuntu),
`gcc`/`librdkafka-devel` (Fedora/RHEL), Xcode Command Line Tools +
`brew install librdkafka` (macOS), e recomendação de WSL ou Microsoft C++
Build Tools (Windows). O passo a passo completo de instalação/execução
fica para a TASK-062, conforme referenciado na Definition of Done desta
tarefa.

## Verificação

- `python3 -m venv` em um diretório temporário seguido de
  `pip install -r requirements.txt` completou com sucesso, sem erros de
  compilação — todas as dependências (incluindo `confluent-kafka`) baixaram
  wheels pré-compilados (`manylinux_2_28_x86_64` / `cp314`) para o ambiente
  de teste (Python 3.14).
- Ambiente virtual de teste removido após a validação.

## Checklist

- [ ] Unit tests pass — N/A, nenhum código de aplicação foi escrito nesta tarefa
- [ ] Integration tests pass — N/A, idem
- [ ] Typecheck passes — N/A, idem
- [ ] Linter passes — N/A, idem

## Próximos passos

TASK-003 (`Dockerfile`/`docker-compose.yml`), que deve instalar estas
mesmas dependências dentro da imagem da aplicação.
