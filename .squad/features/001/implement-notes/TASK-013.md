---
task: TASK-013
story: US-001a
status: done
---

# TASK-013 — `app/api/routes/configurations.py`

## O que foi feito

Criado `app/api/routes/configurations.py` com as rotas `GET
/api/v1/configurations` e `POST /api/v1/configurations`, registradas no
agregador único de `app/api/routes/__init__.py` (TASK-011). Como
`services/kafka_service.py` (TASK-009) ainda não tinha nenhuma operação
de configuração, foi necessário primeiro estendê-lo com dois passthroughs
— é o próprio texto desta tarefa que exige o caminho "via
`services/kafka_service.py`".

```python
# app/services/kafka_service.py — adicionado
def list_configurations() -> list[EnvironmentConfiguration]:
    return config_manager.list_configurations()

def create_configuration(configuration: EnvironmentConfiguration) -> EnvironmentConfiguration:
    return config_manager.create_configuration(configuration)
```

```python
# app/api/routes/configurations.py
router = APIRouter(prefix="/configurations", tags=["configurations"])

@router.get("", response_model=list[ConfigurationResponse])
def list_configurations() -> list[ConfigurationResponse]:
    configurations = kafka_service.list_configurations()
    return [ConfigurationResponse.from_domain(c) for c in configurations]

@router.post("", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
def create_configuration(request: ConfigurationCreateRequest) -> ConfigurationResponse:
    try:
        created = kafka_service.create_configuration(request.to_domain())
    except ConfigurationAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.friendly_message) from error
    return ConfigurationResponse.from_domain(created)
```

Decisões de implementação:

- **`kafka_service.list_configurations`/`create_configuration` como
  passthroughs deliberados**, mesmo sendo só uma linha cada. Não é
  indireção gratuita: é literalmente o que a Definition o Done exige
  ("a rota não chama `config/manager.py` diretamente — passa por
  `services/kafka_service.py`") e o que a seção 3.1 do plano já descrevia
  como regra geral ("`ui/` e `api/` chamam exclusivamente
  `services/kafka_service.py`") — a TASK-009 só tinha testado essa regra
  para `kafka/`, `avro/` e `registry/`; esta tarefa fecha a lacuna para
  `config/manager.py` também (ver abaixo).
- **409 Conflict para nome duplicado**, com `detail` sendo diretamente
  `error.friendly_message` da `ConfigurationAlreadyExistsError` (TASK-008)
  — já em português, já compreensível, sem precisar reformatar nada na
  rota. Não criei um exception handler global no FastAPI para isso: só
  esta rota precisa desse tratamento até agora, e um handler compartilhado
  seria antecipar uma necessidade que ainda não apareceu em nenhuma outra
  tarefa — se as rotas futuras (TASK-018, TASK-022, TASK-029, TASK-035)
  repetirem o mesmo padrão de `try/except` várias vezes, aí sim vale a
  pena consolidar.
- **Erros de campo (nome/bootstrap_servers vazios) não precisaram de
  tratamento manual**: o FastAPI já converte `pydantic.ValidationError` do
  corpo da requisição em HTTP 422 automaticamente, e as mensagens
  amigáveis em português já vêm dos `field_validator`s da TASK-012 —
  confirmado nos testes de rota.
- **Extensão do guarda-corrim arquitetural** (`tests/test_architecture_boundaries.py`,
  criado na TASK-009): adicionei `FORBIDDEN_SUBPATHS = {("config",
  "manager")}` à verificação, distinguindo `config.manager`
  (orquestração/E-S, proibido para `ui/`/`api/`) de `config.models`/
  `config.storage` (tipos de dado puros, já reaproveitados livremente
  desde a TASK-012 em `api/schemas/configurations.py`). A lógica de
  detecção foi generalizada para cobrir `from app.config import manager`
  (nome importado, não só caminho do módulo) além dos casos já cobertos
  (`import app.config.manager`, `from app.config.manager import ...`).
  Sem essa extensão, o guarda-corrim da TASK-009 teria ficado cego para
  exatamente a violação que esta tarefa proíbe explicitamente.

## Verificação

- **`tests/test_kafka_service.py`** (3 casos novos): `list_configurations`/
  `create_configuration` delegam para `config/manager.py`, e a exceção de
  nome duplicado se propaga sem ser engolida.
- **`tests/test_architecture_boundaries.py`** (5 casos novos, testando a
  função de detecção diretamente com strings sintéticas, sem precisar
  escrever arquivos de violação em disco): confirma que `import
  app.config.manager`, `from app.config.manager import ...` e `from
  app.config import manager` são todos detectados como
  `config.manager`, enquanto `config.models`/`config.storage` e
  `fastavro` (que não deve colidir com o segmento "avro") continuam
  liberados. O teste de varredura real (`test_ui_and_api_never_import_...`)
  passa com o arquivo `configurations.py` de verdade já em disco.
- **`tests/test_configurations_route.py`** (novo, via
  `fastapi.testclient.TestClient` sobre o `app` real), cobrindo os três
  itens da Definition of Done:
  - **Salvar e reabrir (cenário 1 de US-001a)**:
    `test_created_configuration_can_be_reopened_via_subsequent_get`.
  - **Nome duplicado rejeitado sem sobrescrever**:
    `test_creating_a_duplicate_name_is_rejected_without_overwriting`
    (POST duplicado retorna 409 com o nome no `detail`, e a listagem
    depois confirma que o `bootstrap_servers` original permanece
    intocado).
  - Casos adicionais: listagem vazia inicial, 201 com o corpo criado,
    422 com mensagem compreensível para `nome`/`bootstrap_servers`
    vazios, e presença das duas rotas no `/openapi.json`.
- `pytest -v` (venv limpo): **102 testes, todos `PASSED`** (15 novos + 87
  já existentes das TASK-005 a TASK-012 — nenhuma regressão).
- **Execução real de ponta a ponta** via `python -m app.main` +
  `curl`: `GET` vazio → `[]`; `POST` → 201 com a configuração criada;
  `GET` seguinte → lista com a mesma configuração (reabertura
  confirmada); `POST` duplicado → 409 com
  `{"detail":"Já existe uma configuração chamada 'Desenvolvimento'."}`,
  sem alterar o registro original. Processo e artefatos temporários
  removidos ao final.

## Checklist

- [x] Unit tests pass — 102/102 (15 novos entre `test_kafka_service.py`,
      `test_architecture_boundaries.py` e `test_configurations_route.py`)
- [ ] Integration tests pass — N/A, verificado via execução real de ponta a ponta (ver seção "Verificação")
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-014 (`app/ui/pages/configuracoes_kafka.py`), que fecha US-001a pelo
lado da interface gráfica, reaproveitando as mesmas rotas/`kafka_service`
criadas aqui.
