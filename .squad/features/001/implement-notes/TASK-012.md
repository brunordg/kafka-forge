---
task: TASK-012
story: US-001a
status: done
---

# TASK-012 — `app/api/schemas/configurations.py`

## O que foi feito

Criado `app/api/schemas/configurations.py` com os contratos HTTP
(request/response) para criar e listar Configurações de Ambiente, seção
6.1 do `plan.md`.

```python
class KafkaConfigPayload(BaseModel): ...          # espelha KafkaConfig
class SchemaRegistryConfigPayload(BaseModel): ...  # espelha SchemaRegistryConfig
class ConfigurationCreateRequest(BaseModel):        # corpo do POST
    nome: str
    kafka: KafkaConfigPayload
    schema_registry: SchemaRegistryConfigPayload | None = None

    def to_domain(self) -> EnvironmentConfiguration: ...

class ConfigurationResponse(BaseModel):             # response_model do GET/POST
    nome: str
    kafka: KafkaConfigPayload
    schema_registry: SchemaRegistryConfigPayload | None = None

    @classmethod
    def from_domain(cls, configuration: EnvironmentConfiguration) -> "ConfigurationResponse": ...
```

Decisões de implementação:

- **Modelos próprios da camada de API (`api/schemas/`), não um reuso
  direto de `config/models.py` (TASK-007)**, com `to_domain()`/
  `from_domain()` fazendo a ponte entre as duas camadas. Isso segue a
  separação já desenhada na árvore do plano (`config/` = modelo de
  domínio persistido; `api/schemas/` = contratos HTTP) e é o que permite
  a este arquivo acrescentar mensagens de erro amigáveis (DoD 3) sem
  alterar o modelo de domínio já testado na TASK-007. Os enums
  `SecurityProtocol`/`SaslMechanism` são reaproveitados diretamente de
  `config/models.py` — são vocabulário estável e duplicá-los criaria risco
  de desalinhamento sem nenhum benefício de desacoplamento real.
- **Nomes de payload neutros (`KafkaConfigPayload`,
  `SchemaRegistryConfigPayload`)**, não `...Request`, porque o mesmo
  formato serve tanto o corpo do `POST` quanto os campos aninhados do
  `ConfigurationResponse` — chamar algo usado numa resposta de "Request"
  seria confuso.
- **Mensagens de erro compreensíveis (DoD 3)** via `field_validator` nos
  três campos mais propensos a erro silencioso — `nome`,
  `bootstrap_servers` e `schema_registry.url` — rejeitando strings vazias
  ou só com espaço com uma frase em português explicando o que falta, em
  vez da mensagem genérica do Pydantic ("String should have at least 1
  character"). Os enums (`security_protocol`, `sasl_mechanism`) já vêm com
  mensagem clara por padrão no Pydantic v2 (lista os valores aceitos), sem
  precisar de validador customizado — confirmado no teste
  `test_invalid_security_protocol_message_lists_the_accepted_values`.
- **Guarda-corrim de cobertura de campos em tempo de import**: três
  `assert set(...Payload.model_fields) == set(...Config.model_fields)` no
  final do próprio módulo — se `config/models.py` ganhar um campo novo
  sem o equivalente aqui, a aplicação falha ao subir (`AssertionError`)
  em vez de silenciosamente expor uma API desatualizada. Mesmo espírito
  guarda-corrim das TASK-009/TASK-011 (verificação estrutural automática
  em vez de só documentação).
- **Secrets (senha, chave privada) aparecem em `ConfigurationResponse`
  como estão armazenados**, sem mascaramento. Decisão consciente: o
  cenário 1 de US-001a exige que "a configuração salva... pode ser
  reaberta posteriormente" (edição precisa dos valores reais para
  preencher o formulário de novo), e a spec já assume, em NFR-003 e
  "Out of Scope", que não há gestão avançada de segredos nem múltiplos
  usuários nesta ferramenta local — inventar um esquema de mascaramento
  não pedido quebraria esse fluxo de reabertura sem que a spec tivesse
  solicitado a troca.

### Sobre a Definition of Done "usados como `response_model`/tipo de corpo
nas rotas de `api/routes/configurations.py`"

Esse arquivo de rotas ainda não existe — é escopo explícito da TASK-013
("Implementar `app/api/routes/configurations.py` com as rotas `GET
/api/v1/configurations` e `POST /api/v1/configurations`"), a próxima
tarefa da fila. Os métodos `to_domain()`/`from_domain()` foram desenhados
especificamente para que a TASK-013 apenas os chame, sem precisar
reimplementar conversão nenhuma. Este item da DoD será cumprido de fato
quando a TASK-013 acontecer; documentado aqui para rastreabilidade, no
mesmo padrão já usado nas notas da TASK-005 (exceções "consumidas" por
tarefas futuras) e da TASK-009 (métodos de `kafka_service.py`
"provisórios" até serem implementados).

## Verificação

- `tests/test_api_schemas_configurations.py` (novo), 14 casos:
  - **Cobertura de campos (DoD 1)**: comparação direta de
    `model_fields` entre cada payload da API e seu correspondente em
    `config/models.py`.
  - **Request válido** com e sem `schema_registry`.
  - **Conversão de/para o domínio**: `to_domain()` produz um
    `EnvironmentConfiguration` equivalente; `ConfigurationResponse.from_domain()`
    faz o caminho inverso, com e sem `schema_registry`.
  - **Mensagens compreensíveis (DoD 3)**: `nome`, `bootstrap_servers` e
    `schema_registry.url` vazios/só-espaço geram a frase em português
    esperada; `security_protocol` inválido lista os valores aceitos;
    `bootstrap_servers` ausente é reportado com o caminho exato do campo
    (`("kafka", "bootstrap_servers")`) em `exc_info.value.errors()`.
- `pytest -v` (venv limpo): **87 testes, todos `PASSED`** (14 novos +
  73 já existentes das TASK-005 a TASK-011 — nenhuma regressão).
- `grep` confirma que `app/api/schemas/configurations.py` não importa
  nada de `ui`, `kafka`, `avro` ou `registry`.
- Ambiente virtual de teste e caches removidos após a validação.

## Checklist

- [x] Unit tests pass — 87/87 (14 novos em
      `tests/test_api_schemas_configurations.py`)
- [ ] Integration tests pass — N/A, módulo é só contrato Pydantic, sem rota HTTP ainda montada (TASK-013)
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-013 (`app/api/routes/configurations.py`), que deve usar
`ConfigurationCreateRequest`/`ConfigurationResponse` como corpo/
`response_model` das rotas `GET /api/v1/configurations` e `POST
/api/v1/configurations`, completando o item 2 da Definition of Done desta
tarefa.
