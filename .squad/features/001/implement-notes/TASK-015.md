---
task: TASK-015
story: US-001b
status: done
---

# TASK-015 — `app/kafka/connection.py`

## O que foi feito

Criado `app/kafka/connection.py`: a factory de client Kafka (Producer e
AdminClient) a partir de uma Configuração de Ambiente, com timeout único
de 10 segundos e suporte a todas as combinações de `security_protocol`
(PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL — decisão Q5: só SASL/PLAIN).

```python
CONNECTION_TIMEOUT_MS = 10_000

def build_client_config(configuration: EnvironmentConfiguration) -> dict: ...
def build_producer(configuration: EnvironmentConfiguration) -> Producer: ...
def build_admin_client(configuration: EnvironmentConfiguration) -> AdminClient: ...
```

Decisões de implementação:

- **`CONNECTION_TIMEOUT_MS = 10_000`** é a única constante usada em duas
  propriedades do `librdkafka`: `socket.connection.setup.timeout.ms`
  (tempo máximo para o handshake TCP+SSL+SASL — a propriedade
  semanticamente mais correta para "timeout de conexão") e
  `socket.timeout.ms` (operações subsequentes no socket já conectado,
  relevante para o `AdminClient.list_topics(...)` que a TASK-017 vai usar
  para testar conexão). As duas sempre referenciam a mesma constante, sem
  nenhum valor duplicado.
- **Certificados guardados como conteúdo PEM em string** (não caminho de
  arquivo), coerente com o modelo `KafkaConfig` da TASK-007: uso das
  propriedades `ssl.ca.pem`/`ssl.certificate.pem`/`ssl.key.pem` do
  `librdkafka` (variantes "inline" das já conhecidas `ssl.*.location`),
  em vez de gravar um arquivo temporário no disco.
- **Bloco SASL (`sasl.mechanisms`/`sasl.username`/`sasl.password`)
  aplicado quando `security_protocol` é `SASL_PLAINTEXT` ou `SASL_SSL`;
  bloco SSL (`ssl.ca.pem`/`ssl.certificate.pem`/`ssl.key.pem`/
  `ssl.key.password`) aplicado quando é `SSL` ou `SASL_SSL`** — os dois
  blocos são independentes e podem coexistir (`SASL_SSL`), cobrindo
  "qualquer combinação suportada" exigida pela DoD sem `if/elif`
  excludentes.
- **`sasl.mechanism` tem default `PLAIN`** quando `kafka.sasl_mechanism`
  não foi informado mas o protocolo exige SASL — evita depender do
  desenvolvedor lembrar de preencher um campo cujo único valor válido
  hoje é `PLAIN` (decisão Q5).
- **Detecção de certificado sem senha de chave privada (DoD 3)**: checagem
  puramente textual dos cabeçalhos PEM padrão que indicam criptografia —
  `-----BEGIN ENCRYPTED PRIVATE KEY-----` (PKCS#8) e `Proc-Type:
  4,ENCRYPTED` (PKCS#1 tradicional) — sem depender de nenhuma biblioteca
  de criptografia adicional. A checagem roda dentro de
  `build_client_config`, **antes** de qualquer propriedade `ssl.*` ser
  adicionada ao dicionário e, portanto, antes de qualquer chance de
  `build_producer`/`build_admin_client` tentarem de fato um handshake TLS
  — levanta `KafkaAuthenticationError` (TASK-005) com uma mensagem que já
  aponta o campo especificamente (`client_key_password`). A checagem só
  roda quando `security_protocol` envolve SSL — um `client_key`
  preenchido "por engano" numa configuração `PLAINTEXT` (permitido pelo
  modelo da TASK-007, que não faz validação cruzada) é simplesmente
  ignorado, nunca usado nem checado. A TASK-016 (próxima) deve refinar o
  comportamento específico dessa exceção em `app/exceptions.py`; esta
  tarefa já entrega a detecção funcionando de ponta a ponta com uma
  mensagem compreensível.

## Verificação

- **`tests/test_kafka_connection.py`** (novo), 20 casos:
  - **Timeout único e reutilizável (DoD 2)**: confirma
    `CONNECTION_TIMEOUT_MS == 10_000` e que as duas propriedades do
    `librdkafka` recebem exatamente essa constante.
  - **Todas as combinações de `security_protocol` (DoD 1)**: PLAINTEXT
    sem nenhuma propriedade `sasl.`/`ssl.`; SSL com certificados; SASL_PLAINTEXT
    com credenciais; SASL_SSL combinando os dois blocos; default de
    `sasl.mechanisms` para `PLAIN`.
  - **Certificado sem senha quando a chave exige (DoD 3)**: chave PKCS#8
    e PKCS#1 criptografadas sem senha são rejeitadas com
    `KafkaAuthenticationError` apontando `client_key_password`; a mesma
    chave COM senha é aceita; uma chave não criptografada sem senha
    também é aceita (a checagem não gera falso positivo); a checagem é
    pulada para protocolos sem SSL.
  - **Construção real de clientes `librdkafka`** (sem precisar de um
    broker): `build_producer`/`build_admin_client` parametrizados pelas 4
    combinações de `security_protocol` — cada chamada de fato instancia
    `confluent_kafka.Producer`/`confluent_kafka.admin.AdminClient`, o que
    valida que todos os nomes de propriedade usados
    (`ssl.ca.pem`, `ssl.certificate.pem`, `ssl.key.pem`,
    `sasl.mechanisms`, `socket.connection.setup.timeout.ms`) são aceitos
    de verdade pela biblioteca nativa `librdkafka` — não só por uma
    suposição de nomenclatura.
- `pytest -v` (venv limpo, instalado só a partir de
  `requirements-dev.txt`): **128 testes, todos `PASSED`** (20 novos + 108
  já existentes — nenhuma regressão).
- `grep` confirma que `app/kafka/connection.py` não importa nada de `ui`
  ou `api` (as únicas dependências são `app.config.models` e
  `app.exceptions`, ambos módulos de dados/domínio permitidos).
- Ambiente virtual de teste e caches removidos após a validação.

## Checklist

- [x] Unit tests pass — 128/128 (20 novos em `tests/test_kafka_connection.py`)
- [ ] Integration tests pass — N/A, construção de cliente validada sem
      broker real (ver seção "Verificação"); teste de conectividade fim a
      fim contra um Kafka real fica para a TASK-060
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-016 (extensão específica de `KafkaAuthenticationError` em
`app/exceptions.py` para o cenário de certificado sem senha) e TASK-017
(`services/kafka_service.test_connection`, usando `build_admin_client`
deste módulo para testar conectividade de verdade contra um broker, sem
publicar nada — NFR-002).
