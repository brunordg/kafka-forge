---
task: TASK-009
story: N/A (fundação; pré-requisito de todas as stories P1/P2/P3)
status: done
---

# TASK-009 — Esqueleto de `app/services/kafka_service.py`

## O que foi feito

Criado `app/services/kafka_service.py` como o ponto único de orquestração
descrito nas seções 3.1 e 3.4 do `plan.md`, com as assinaturas dos cinco
métodos que serão implementados nas fases seguintes:
`test_connection`, `test_schema_registry`, `validate_schema`,
`validate_payload` e `publish`. Também foram criados dois testes de
infraestrutura: `tests/test_kafka_service.py` (comportamento do
esqueleto) e `tests/test_architecture_boundaries.py` (guarda-corrim
arquitetural que impede `ui/`/`api/` de importar `kafka/`, `avro/` ou
`registry/` diretamente).

### `app/services/kafka_service.py`

Módulo de funções (não uma classe), seguindo o mesmo estilo já usado em
`config/manager.py` e `config/storage.py`:

```python
def test_connection(nome_configuracao: str) -> ConnectionTestResult: ...
def test_schema_registry(nome_configuracao: str) -> ConnectionTestResult: ...
def validate_schema(avsc_content: str) -> SchemaValidationResult: ...
def validate_payload(schema_avsc: str, payload: dict) -> PayloadValidationResult: ...
def publish(nome_configuracao, topic, schema_avsc, payload, key=None) -> PublishResult: ...
```

Cada método tem um `dataclass` de retorno próprio
(`ConnectionTestResult`, `SchemaValidationResult`,
`PayloadValidationResult`, `PublishResult`) — deliberadamente simples e
sinalizados como provisórios nas docstrings, para não travar decisões que
pertencem às tarefas que de fato os implementam (TASK-017, TASK-021,
TASK-028, TASK-034).

Decisões de implementação:

- **Módulo de funções, não classe.** Não há necessidade de estado de
  instância — `config/manager.py` (TASK-008) já lê `configurations.json`
  do zero a cada chamada, sem cache. Manter `kafka_service.py` como
  funções soltas evita a tentação de guardar um objeto de configuração
  "atual" como atributo de instância, que é exatamente o padrão que
  causaria o problema de concorrência UI+API citado na seção 11 do plano.
- **`_get_configuration_snapshot(nome_configuracao)`**: função privada
  única que todo método com dependência de Configuração de Ambiente
  (`test_connection`, `test_schema_registry`, `publish`) chama para obter
  os dados — sempre via `config_manager.get_configuration(nome)`, nunca
  guardando o resultado em variável de módulo. `validate_schema` e
  `validate_payload` não recebem nome de configuração porque validam
  schema/payload isoladamente, sem depender de Kafka ou Schema Registry.
- **Corpo provisório levanta `NotImplementedError`** com uma mensagem
  apontando a tarefa que vai implementar de verdade, em vez de retornar
  um resultado falso de sucesso — evita que qualquer consumidor futuro
  (UI/API) confunda "ainda não implementado" com "funcionou". Antes de
  levantar a exceção, os três métodos que dependem de configuração já
  resolvem o snapshot de verdade (via `config_manager.get_configuration`,
  já funcional desde a TASK-008), então uma configuração inexistente
  continua propagando `ConfigurationNotFoundError` normalmente, mesmo
  neste estágio provisório.

### `tests/test_kafka_service.py` (novo)

- Confirma que os cinco métodos existem e ainda levantam
  `NotImplementedError` (implementação provisória, não um sucesso
  fingido).
- Confirma que `test_connection`/`publish` com uma configuração
  inexistente propagam `ConfigurationNotFoundError` — prova de que a
  leitura de configuração já está de fato ligada a `config/manager.py`.
- Confirma a leitura por snapshot exigida pela DoD com dois tipos de
  teste: (1) espiando `config_manager.get_configuration` via
  `monkeypatch` e conferindo que é chamado a cada invocação (sem cache);
  (2) um teste mais forte que atualiza a configuração entre duas chamadas
  e confirma que a segunda chamada enxerga o valor novo
  (`bootstrap_servers` mudou de `"original:9092"` para
  `"atualizado:9092"`), provando que não existe referência mutável
  compartilhada entre chamadas.

### `tests/test_architecture_boundaries.py` (novo)

Varre `app/ui/` e `app/api/` com `ast` (não regex, para evitar falsos
positivos/negativos em strings ou comentários) procurando qualquer
`import`/`from ... import ...` cujo primeiro segmento — ou segundo
segmento após `app.` — seja `kafka`, `avro` ou `registry`. Falha o teste
com a lista de arquivos/violações encontradas, citando a NFR-006. Hoje
`ui/` e `api/` só têm `.gitkeep`, então o teste passa vazio; ele existe
como guarda-corrim para todas as tarefas seguintes que forem popular
essas pastas (TASK-013, TASK-014, TASK-018, TASK-019, ...).

## Verificação

- `pytest -v` (venv limpo): **56 testes, todos `PASSED`** (10 novos em
  `test_kafka_service.py` + 1 novo em `test_architecture_boundaries.py` +
  45 já existentes das TASK-005 a TASK-008 — nenhuma regressão).
- **Teste do teste**: criei temporariamente
  `app/ui/pages/_violacao_temporaria.py` com
  `from app.kafka.connection import build_producer` e rodei
  `test_architecture_boundaries.py` isoladamente — o teste **falhou**
  como esperado, apontando exatamente o arquivo e o módulo proibido
  (`app/ui/pages/_violacao_temporaria.py: ['kafka']`). Arquivo removido
  em seguida e a suíte completa voltou a passar 100%, confirmando que a
  verificação não é vazia/inofensiva por acidente.
- Ambiente virtual de teste e caches removidos após a validação.

## Checklist

- [x] Unit tests pass — 56/56 (11 novos entre `test_kafka_service.py` e
      `test_architecture_boundaries.py`)
- [ ] Integration tests pass — N/A, módulo ainda não integra com Kafka/Schema Registry reais (implementação provisória)
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-010 (módulo de log estruturado de operações) e TASK-011 (rota
`GET /api/v1/health` + registro de rotas em `main.py`), que fecham a Fase
2 — Fundação. As implementações reais de cada método de
`kafka_service.py` chegam a partir da TASK-017 (`test_connection`),
TASK-021 (`validate_schema`), TASK-028 (`validate_payload`), TASK-034
(`publish`) e TASK-046 (`test_schema_registry`).
