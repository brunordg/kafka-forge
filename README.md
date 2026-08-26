# KafkaForge

Ferramenta local de apoio ao desenvolvimento para configurar uma conexão
com o Kafka corporativo (e, opcionalmente, um Schema Registry), carregar e
validar schemas Avro, montar e validar payloads, e publicar mensagens em
tópicos Kafka — pela interface web ou por um serviço REST local que outras
automações podem chamar.

## 1. Objetivo

Eliminar a necessidade de scripts avulsos para testar publicações Avro
durante o desenvolvimento: uma única ferramenta local cobre configuração de
conexão (Kafka + Schema Registry), upload/validação de `.avsc`, montagem e
validação de payload, publicação e histórico — tanto por uma tela quanto
por uma API REST equivalente.

## 2. Arquitetura

```text
Desenvolvedor (navegador)              Script / Automação
        │                                      │
        ▼                                      │ HTTP
   NiceGUI (ui/)                                ▼
        │                              FastAPI (api/)
        └───────────────┬──────────────────────┘
                         ▼
                services/kafka_service.py
                 (orquestração única)
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   avro/                registry/       kafka/
   schema_loader.py     client.py       connection.py
   validator.py         (Schema         producer.py
   schema_store.py       Registry)      serializer.py
        │                    │                │
        └────────────────────┴────────────────┘
                         │
              config/ (manager.py, models.py)
                         │
                 armazenamento local
           (~/.kafkaforge: configurations.json,
            schemas/*.avsc, logs/operacoes-*.jsonl)
```

`ui/` e `api/` nunca chamam `kafka/`, `avro/` ou `registry/` diretamente —
só `services/kafka_service.py`, que é o único ponto que orquestra
validação → serialização → Schema Registry → publicação. Isso garante que
a interface gráfica e o serviço local produzem sempre o mesmo resultado
para a mesma entrada. Sem banco de dados: tudo fica em arquivos locais sob
`~/.kafkaforge` (ou o diretório apontado por `KAFKAFORGE_HOME`).

## 3. Como instalar

Pré-requisitos: Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Pré-requisitos por sistema operacional (`confluent-kafka`)

A dependência `confluent-kafka` (bindings Python de `librdkafka`) distribui
wheels pré-compilados para as combinações mais comuns de SO/arquitetura
(Linux x86_64/arm64, macOS, Windows), então na maioria dos casos o `pip
install` acima funciona sem nenhum toolchain de build instalado. Caso o
`pip` não encontre um wheel compatível com o seu ambiente e precise
compilar `confluent-kafka`/`librdkafka` a partir do código-fonte, instale
previamente:

- **Linux (Debian/Ubuntu)**: `sudo apt-get install -y build-essential python3-dev librdkafka-dev`
- **Linux (Fedora/RHEL)**: `sudo dnf install -y gcc gcc-c++ python3-devel librdkafka-devel`
- **macOS**: Xcode Command Line Tools (`xcode-select --install`) e
  `brew install librdkafka`
- **Windows**: recomenda-se usar o WSL (Windows Subsystem for Linux) com uma
  distribuição Linux suportada acima; alternativamente, instalar o
  "Microsoft C++ Build Tools" para compilar a extensão nativamente

## 4. Como executar

Localmente:

```bash
cp .env.example .env   # opcional — ajuste KAFKAFORGE_HOME/APP_PORT se quiser
python -m app.main
```

A aplicação sobe em `http://127.0.0.1:8080` (interface e API no mesmo
processo/porta) e nunca faz bind fora de `127.0.0.1` (NFR-001).

Via Docker Compose (só a aplicação, por padrão):

```bash
docker compose up --build
```

Opcionalmente, para desenvolvimento/testes sem um Kafka/Schema Registry
corporativo à mão, é possível subir um Kafka e um Schema Registry locais
via Docker também:

```bash
docker compose --profile local-infra up
```

Isso não é necessário para uso contra um Kafka corporativo real — a
aplicação se conecta a qualquer broker alcançável pela rede do
desenvolvedor (VPN ou equivalente).

## 5. Como configurar Kafka

Na tela **Configurações → Kafka** (`/configuracoes/kafka`):

1. Informe um **nome** para a configuração (ex.: `Desenvolvimento`,
   `Homologação`, `Produção`).
2. Informe o **endereço dos brokers** (`bootstrap_servers`, ex.:
   `broker1:9092,broker2:9092`).
3. Escolha o **protocolo de segurança** (`PLAINTEXT`, `SSL`,
   `SASL_PLAINTEXT` ou `SASL_SSL`) — ver seções 6–8 abaixo.
4. Clique em **Salvar**. A configuração fica disponível na lista abaixo,
   podendo ser reaberta para edição ou removida.
5. Clique em **Testar conexão** para confirmar que a ferramenta consegue
   alcançar o broker informado — o teste só consulta metadados (nunca
   publica uma mensagem).

Cada nome de configuração precisa ser único; tentar salvar um nome já
existente é recusado sem sobrescrever a configuração original.

## 6. Como configurar SSL

Com **Protocolo de segurança = SSL**, faça upload do **Certificado da
autoridade (CA)** que assina o certificado do broker. Se o broker também
exigir autenticação do cliente (mTLS), veja a seção 7.

## 7. Como configurar mTLS

Com **Protocolo de segurança = SSL** (ou `SASL_SSL`), além do certificado
CA:

1. Faça upload do **Certificado do cliente**.
2. Faça upload da **Chave privada do cliente**.
3. Se a chave privada exigir senha, informe-a em **Senha da chave
   privada**. Se a chave exigir senha e o campo ficar vazio, o **Testar
   conexão** falha com uma mensagem específica apontando esse campo — não
   um erro genérico de SSL.

## 8. Como configurar SASL

Com **Protocolo de segurança = SASL_PLAINTEXT** ou **SASL_SSL**:

1. Escolha o **mecanismo SASL** (`PLAIN` nesta versão).
2. Informe **Usuário** e **Senha**.
3. Com `SASL_SSL`, configure também o certificado CA (seção 6) e,
   se necessário, mTLS (seção 7).

## 9. Como configurar Schema Registry

Na tela **Configurações → Schema Registry** (`/configuracoes/schema-registry`):

1. Selecione a **Configuração de ambiente** já cadastrada (seção 5) cujo
   Schema Registry você quer configurar — é um bloco independente do
   bloco Kafka da mesma configuração.
2. Informe a **URL** do Schema Registry e, se aplicável, **usuário**,
   **senha** e certificados (CA / cliente / chave privada do cliente, para
   mTLS contra o próprio Schema Registry).
3. Clique em **Salvar** e depois em **Testar Schema Registry** para
   confirmar que ele está acessível — o teste só consulta a lista de
   subjects (nunca registra nem altera nada).

O Schema Registry é opcional: um ambiente sem ele configurado continua
publicando normalmente, serializando diretamente a partir do `.avsc`
carregado (sem exigir Schema Registry).

Publicar também nunca registra um schema novo no Schema Registry: se o
schema usado já existir lá (por conteúdo idêntico sob o subject), a
mensagem é publicada com o id do Schema Registry; se ainda não existir, a
publicação não é bloqueada — o schema local continua servindo só para
validar o payload, e a mensagem é publicada sem vínculo com o Schema
Registry (o status da tela deixa isso explícito).

## 10. Como carregar um `.avsc`

Na tela **Schemas Avro** (`/schemas/avro`), faça upload de um arquivo
`.avsc`. A ferramenta valida a estrutura e exibe nome, namespace, campos
(com tipos, incluindo tipos compostos: union, enum, array, map, record) e
o conteúdo original. Um schema inválido é rejeitado com uma explicação
compreensível, sem travar as demais telas.

Todo schema carregado com sucesso fica disponível por nome (o `name`
declarado no `.avsc`) para ser selecionado depois em **Publicar Mensagem**
ou referenciado pela API (seção 13), sem precisar subir o arquivo de novo.

Como alternativa ao upload, com um Schema Registry configurado (seção 9),
a mesma tela permite selecionar um **subject** já existente no registry em
vez de subir um novo arquivo.

## 11. Como criar um payload

Na tela **Publicar Mensagem** (`/publicar-mensagem`), depois de selecionar
um schema (por upload ou pela lista de schemas já carregados):

- Use o **editor JSON** para digitar o payload diretamente, ou
- Use o **formulário gerado automaticamente** (um campo por atributo do
  schema) — os dois preenchem o mesmo payload; o formulário só cobre
  campos de tipo primitivo (string, int, long, float, double, boolean,
  bytes), campos de tipo composto (union genérica, enum, array, map,
  record) continuam editáveis apenas pelo editor JSON.

Campos `bytes` são representados no JSON como uma string em **base64**.

## 12. Como enviar uma mensagem

Ainda em **Publicar Mensagem**: escolha a **Configuração**, informe o
**Tópico** e, opcionalmente, uma **Chave**. Clique em **Validar** para
conferir o payload contra o schema sem publicar nada, ou diretamente em
**Publicar**. Uma publicação bem-sucedida mostra tópico, partição e offset
retornados pelo Kafka; uma falha mostra uma mensagem compreensível (tópico
inexistente, conexão perdida, payload inválido etc.).

## 13. Como utilizar a API

Com a aplicação em execução, a documentação interativa (Swagger UI) fica
em `http://127.0.0.1:8080/docs` — também acessível pela tela **API** do
menu lateral. Todas as operações disponíveis pela tela também estão
disponíveis pela API (paridade UI/API):

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/health` | estado do serviço |
| GET | `/api/v1/configurations` | lista configurações salvas |
| POST | `/api/v1/configurations` | cria uma configuração |
| DELETE | `/api/v1/configurations/{name}` | remove uma configuração |
| POST | `/api/v1/configurations/{name}/test` | testa Kafka e (se configurado) Schema Registry |
| POST | `/api/v1/schema/validate` | valida um `.avsc` enviado no corpo |
| POST | `/api/v1/messages/validate` | valida um payload contra um `.avsc`, sem publicar |
| POST | `/api/v1/messages` | valida → serializa → publica |
| GET | `/api/v1/logs` | histórico de operações (opcionalmente filtrado) |

## 14. Exemplos de `curl`

Criar uma configuração:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/configurations \
  -H "Content-Type: application/json" \
  -d '{
        "nome": "Desenvolvimento",
        "kafka": {
          "bootstrap_servers": "localhost:9092",
          "security_protocol": "PLAINTEXT"
        }
      }'
```

Testar a conexão:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/configurations/Desenvolvimento/test
```

Carregar (e persistir) um schema — pela tela **Schemas Avro**, ou validando
via API e depois carregando pela tela; a API de validação não persiste o
schema por si só, sendo puramente uma inspeção (use a tela para tornar o
schema selecionável por nome).

Validar um payload:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/messages/validate \
  -H "Content-Type: application/json" \
  -d '{
        "avsc_content": "{\"type\":\"record\",\"name\":\"Pedido\",\"fields\":[{\"name\":\"id\",\"type\":\"long\"},{\"name\":\"cliente\",\"type\":\"string\"},{\"name\":\"valor\",\"type\":\"double\"}]}",
        "payload": {"id": 123, "cliente": "João", "valor": 199.90}
      }'
```

Publicar uma mensagem (schema já carregado pela tela, com o nome
`Pedido`):

```bash
curl -X POST http://127.0.0.1:8080/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
        "configuration": "Desenvolvimento",
        "topic": "pedido-criado",
        "schema": "Pedido",
        "payload": {"id": 123, "cliente": "João", "valor": 199.90}
      }'
```

Resposta de sucesso:

```json
{ "success": true, "topic": "pedido-criado", "partition": 2, "offset": 12345 }
```

Resposta de erro:

```json
{ "success": false, "error": "Mensagem incompatível com o schema Avro" }
```

## 15. Exemplos de schemas Avro

Schema simples (tipos primitivos):

```json
{
  "type": "record",
  "name": "Pedido",
  "namespace": "com.example",
  "fields": [
    { "name": "id", "type": "long" },
    { "name": "cliente", "type": "string" },
    { "name": "valor", "type": "double" }
  ]
}
```

Schema com campo opcional (`["null", "string"]`), enum, array, map e
record aninhado (tipos compostos, US-002b):

```json
{
  "type": "record",
  "name": "Pedido",
  "namespace": "com.example",
  "fields": [
    { "name": "id", "type": "long" },
    { "name": "observacao", "type": ["null", "string"], "default": null },
    {
      "name": "status",
      "type": { "type": "enum", "name": "Status", "symbols": ["NOVO", "PAGO", "CANCELADO"] }
    },
    { "name": "itens", "type": { "type": "array", "items": "string" } },
    { "name": "metadados", "type": { "type": "map", "values": "string" } },
    {
      "name": "endereco",
      "type": {
        "type": "record",
        "name": "Endereco",
        "fields": [
          { "name": "rua", "type": "string" },
          { "name": "cidade", "type": "string" }
        ]
      }
    }
  ]
}
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

A suíte cobre carregamento/validação de `.avsc`, validação de payload
(incluindo union opcional, campos extras/ausentes e `bytes` em base64),
serialização Avro, configuração Kafka (SSL/SASL), Schema Registry, o
serviço `services/kafka_service.py`, todas as rotas da API e as telas da
interface — sem depender de um Kafka/Schema Registry real (usam dublês
determinísticos). Testes de integração de ponta a ponta contra um Kafka e
um Schema Registry reais (`docker compose --profile local-infra up`) ficam
como roteiro de validação manual, não como parte da suíte automatizada.

## O que está fora de escopo

Autenticação de usuários/OAuth/RBAC para a própria ferramenta, integração
com gestores corporativos de segredos (Vault ou equivalente), banco de
dados, multi-tenancy e observabilidade distribuída — ver `Assumptions` e
`Out of Scope` em `.squad/features/001/spec.md`.
