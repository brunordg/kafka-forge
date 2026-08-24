---
task: TASK-005
story: N/A (tarefa de infraestrutura; consumida por todas as stories P1/P2)
status: done
---

# TASK-005 — `app/exceptions.py`

## O que foi feito

Criado `app/exceptions.py` com a hierarquia base de exceções de domínio da
seção 8 do `plan.md`. Todas herdam de uma classe base comum,
`KafkaForgeError`, que centraliza o contrato exigido por FR-026: cada
exceção carrega separadamente uma mensagem amigável (`friendly_message`)
para o desenvolvedor e um detalhe técnico bruto (`technical_detail`) para
o Registro de Operação/tela de Logs.

```python
class KafkaForgeError(Exception):
    def __init__(self, friendly_message: str, technical_detail: str = "") -> None:
        super().__init__(friendly_message)
        self.friendly_message = friendly_message
        self.technical_detail = technical_detail


class KafkaConnectionError(KafkaForgeError): ...
class KafkaAuthenticationError(KafkaForgeError): ...
class KafkaAuthorizationError(KafkaForgeError): ...
class SchemaRegistryError(KafkaForgeError): ...
class AvroSchemaError(KafkaForgeError): ...
class AvroValidationError(KafkaForgeError): ...
class MessageSerializationError(KafkaForgeError): ...
class MessagePublishError(KafkaForgeError): ...
```

`technical_detail` tem default `""` para permitir levantar a exceção
mesmo quando o detalhe técnico ainda não está disponível no ponto de
`raise` (ex.: antes de capturar a exceção original de uma biblioteca
externa), sem exigir chamadas em duas etapas.

As oito classes citadas na tarefa herdam diretamente de `KafkaForgeError`
em vez de duplicar o `__init__`, satisfazendo a DoD "cada classe de
exceção aceita separadamente uma mensagem amigável e um detalhe técnico"
por herança — sem repetição de código entre elas. O comportamento
específico de `KafkaAuthenticationError` para o cenário de certificado sem
senha de chave privada (cenário 3 de US-001b) fica para a TASK-016, que
deve estender este módulo sem alterar a hierarquia aqui criada.

## Arquivos adicionais (infraestrutura de teste)

Esta é a primeira tarefa do projeto com cobertura de teste unitário
exigida pela Definition of Done, então também foi necessário introduzir a
infraestrutura mínima de testes, ainda inexistente:

- **`requirements-dev.txt`** (novo): `-r requirements.txt` + `pytest==9.1.1`.
  Mantido separado de `requirements.txt` para não alterar o conjunto de
  bibliotecas de produção fixado na TASK-002 (seção 10.1 do plano lista
  exatamente `nicegui`, `fastapi`, `uvicorn`, `confluent-kafka`,
  `fastavro`, `pydantic` — `pytest` é ferramenta de desenvolvimento, não
  dependência de execução da aplicação).
- **`pyproject.toml`** (novo): configuração mínima do pytest
  (`[tool.pytest.ini_options]`, `pythonpath = ["."]`, `testpaths =
  ["tests"]`) para que `tests/` consiga importar `app.exceptions` sem
  exigir `app/__init__.py` (pacote de namespace implícito do Python 3) nem
  manipulação manual de `PYTHONPATH`.
- **`tests/test_exceptions.py`** (novo): cobertura parametrizada para as
  oito subclasses, verificando que, após a exceção ser capturada em um
  `try/except`, tanto `friendly_message` quanto `technical_detail` ficam
  acessíveis com os valores originais; mais um teste de subclassamento de
  `KafkaForgeError` e um teste do default de `technical_detail`.

## Verificação

- `pytest -v` (em venv limpo, com `requirements-dev.txt` instalado): 17
  testes, todos `PASSED`.
- `grep` confirma que `app/exceptions.py` não importa nada de `ui`, `api`,
  `kafka`, `avro` ou `registry` — módulo completamente independente,
  conforme a regra arquitetural da seção 3.1 do plano.
- Ambiente virtual de teste, cache do pytest e `__pycache__` removidos após
  a validação.

## Checklist

- [x] Unit tests pass — 17/17 testes de `tests/test_exceptions.py`
- [ ] Integration tests pass — N/A, módulo não depende de nenhum sistema externo
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-006 (armazenamento local em `~/.kafkaforge/`) e TASK-007/TASK-008
(`config/models.py`, `config/manager.py`), que dão sequência à Fase 1/2 do
plano. `requirements-dev.txt`/`pyproject.toml` introduzidos aqui já ficam
disponíveis para toda a cobertura de teste das tarefas seguintes
(TASK-016, TASK-058, TASK-059, TASK-061, entre outras).
