---
task: TASK-007
story: N/A (fundação; pré-requisito direto de US-001a, US-005a e US-006)
status: done
---

# TASK-007 — `app/config/models.py`

## O que foi feito

Criado `app/config/models.py` com os modelos Pydantic da **Configuração de
Ambiente** descrita na seção 5 do `plan.md`: bloco Kafka obrigatório e
bloco `schema_registry` opcional e independente (FR-005).

```python
class SecurityProtocol(str, Enum):
    PLAINTEXT = "PLAINTEXT"
    SSL = "SSL"
    SASL_PLAINTEXT = "SASL_PLAINTEXT"
    SASL_SSL = "SASL_SSL"


class SaslMechanism(str, Enum):
    PLAIN = "PLAIN"


class KafkaConfig(BaseModel):
    bootstrap_servers: str
    security_protocol: SecurityProtocol
    sasl_mechanism: SaslMechanism | None = None
    username: str | None = None
    password: str | None = None
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None
    client_key_password: str | None = None


class SchemaRegistryConfig(BaseModel):
    url: str
    username: str | None = None
    password: str | None = None
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None


class EnvironmentConfiguration(BaseModel):
    nome: str
    kafka: KafkaConfig
    schema_registry: SchemaRegistryConfig | None = None
```

Decisões de implementação:

- **`SaslMechanism` como `str, Enum` com um único membro (`PLAIN`)**:
  satisfaz a decisão Q5 (seção 7 do plano) de suportar só usuário/senha
  nesta etapa. Por ser um `Enum` comum, adicionar `SCRAM_SHA_256` etc. no
  futuro é só acrescentar um membro — nenhuma outra parte do modelo
  depende da cardinalidade do enum, então não há nada para "quebrar".
- **`client_key_password` permanece opcional sem nenhuma validação
  cruzada com `client_key`.** Isso é proposital e está escrito
  explicitamente na seção 5 do plano: "`client_key_password` opcional
  mesmo quando a chave a exige — validado apenas no teste de conexão
  (US-001b, cenário 3)". Ou seja, o Pydantic **não** deve rejeitar um
  `client_key` sem senha — essa checagem semântica é responsabilidade da
  TASK-016 (`KafkaAuthenticationError` específico), executada só no
  momento de testar a conexão de fato, não na validação estrutural do
  modelo.
- **`schema_registry: SchemaRegistryConfig | None = None`**: bloco
  totalmente ausente é um valor válido (FR-005/FR-007), sem exigir nenhum
  campo do Kafka ser alterado.
- **`Field(min_length=1)`** em `nome`, `bootstrap_servers` e
  `SchemaRegistryConfig.url`: evita configurações "vazias" que passariam
  a validação de tipo mas seriam inúteis na prática (ex.: `nome=""`).
  Unicidade de nome entre configurações (edge case de US-006) continua
  sendo responsabilidade de `config/manager.py` (TASK-008), não deste
  modelo — um único registro isolado não tem como saber se seu nome é
  único.

## Verificação

- `tests/test_config_models.py` (novo), 11 casos cobrindo:
  - configuração completa válida, com e sem `schema_registry`;
  - `KafkaConfig` só com os dois campos obrigatórios (demais ficam `None`);
  - `client_key` definido sem `client_key_password` — aceito sem erro,
    confirmando a decisão descrita acima;
  - rejeição de `bootstrap_servers` ausente/vazio;
  - rejeição de `security_protocol` e `sasl_mechanism` fora do enum;
  - rejeição de `nome` ausente/vazio em `EnvironmentConfiguration`;
  - rejeição de `SchemaRegistryConfig` sem `url`.
- `pytest -v` (venv limpo): **33 testes, todos `PASSED`** (11 novos +
  22 já existentes das TASK-005/TASK-006 — nenhuma regressão).
- `grep` confirma que `app/config/models.py` não importa nada de `ui`,
  `api`, `kafka`, `avro` ou `registry`.
- Ambiente virtual de teste e caches removidos após a validação.

## Checklist

- [x] Unit tests pass — 33/33 (11 novos em `tests/test_config_models.py`)
- [ ] Integration tests pass — N/A, módulo não depende de nenhum sistema externo
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-008 (`app/config/manager.py`), que deve usar
`EnvironmentConfiguration` deste módulo junto com
`app/config/storage.py` (TASK-006) para implementar o CRUD real sobre
`configurations.json`, incluindo a validação de unicidade de nome que
este modelo deliberadamente não faz sozinho.
