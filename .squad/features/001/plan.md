---
stage: plan
status: approved
sourceSkill:
  id: speckit-plan
  version: dcc8053aa4377cca5f4f2b04a68a27da1eed26203564b92351c7343d54db6eef
approvedBy: bruno
approvedAt: '2026-08-23T00:55:49.129Z'
---

# Plano Técnico: KafkaForge — Envio de Mensagens Avro para o Kafka Corporativo

**Feature**: 001
**Diretório**: `.squad/features/001`
**Especificação**: `.squad/features/001/spec.md`
**Briefing**: `.squad/features/001/briefing.md`
**Clarificações**: `.squad/features/001/clarification.md`
**Stories**: `.squad/features/001/stories/US-001a.md` … `.squad/features/001/stories/US-007b.md`
**Plano**: `.squad/features/001/plan.md` (este arquivo)
**Criado em**: 2026-08-22
**Status**: Draft

> Este repositório não é um repositório Git e não possui o scaffold `.specify/`
> (sem `setup-plan.sh` nem template de `IMPL_PLAN`). Este plano foi montado
> diretamente sobre as convenções `.squad/` já em uso pelo projeto, consolidando
> em um único documento os artefatos que o workflow speckit-plan normalmente
> distribui entre `research.md`, `data-model.md`, `contracts/` e `quickstart.md`.

## Extension Hooks

Nenhum hook encontrado: `.specify/extensions.yml` não existe no diretório do
projeto. Etapa de hooks (pré e pós-plano) ignorada silenciosamente.

---

## 1. Contexto Técnico

A stack e a arquitetura de alto nível já foram decididas no briefing aprovado
(`.squad/features/001/briefing.md`) e são tratadas aqui como restrição de
entrada, não como escolha em aberto.

| Aspecto | Decisão |
|---|---|
| Linguagem/runtime | Python 3.12+ |
| Interface gráfica | NiceGUI (SPA servida localmente) |
| API de automação | FastAPI, com documentação automática em `/docs` |
| Cliente Kafka | `confluent-kafka` (bindings de `librdkafka`) |
| Avro (parse/validação/serialização) | `fastavro` (ou biblioteca equivalente) |
| Cliente de Schema Registry | cliente Confluent Schema Registry (`confluent-kafka[schema-registry]` / `confluent-kafka.schema_registry`) |
| Modelos e validação de dados | Pydantic |
| Persistência | arquivos locais (JSON); **sem** banco de dados |
| Empacotamento | Dockerfile + docker-compose.yml (opcional; sobe só a aplicação por padrão) |
| Execução | inteiramente local, um único desenvolvedor por instância |

Todos os pontos que ficaram subespecificados na spec original (`spec.md`)
foram resolvidos no estágio de clarificação (`clarification.md`) e são
tratados como decisões de arquitetura vinculantes para este plano — ver
seção 8.

**Restrições não-funcionais que moldam a arquitetura** (da spec):
NFR-001 (tudo local, nenhum dado sai para terceiros além do Kafka/Schema
Registry configurados), NFR-002 (testes de conexão sem efeito colateral),
NFR-003 (segredos ficam só na configuração local), NFR-004 (timeouts
curtos e previsíveis), NFR-005 (zero infraestrutura extra), NFR-006
(paridade de comportamento entre UI e serviço local).

---

## 2. Constitution Check

`.squad/constitution.md` v1.0.0 (ratificada em 2026-08-22) formaliza os
princípios que este plano já vinha seguindo informalmente. Checando este
plano contra os cinco princípios ratificados:

- **I. Ferramenta Local, Sem Infraestrutura Extra** — persistência via arquivos locais (JSON), sem banco de dados nem infra além do Kafka/Schema Registry corporativos. ✅ respeitado (seção 6 e 10).
- **II. Sem Overengineering** — uma camada de serviço fina compartilhada entre UI e API, sem abstrações especulativas (ex.: sem plugin system, sem multi-tenancy). ✅ respeitado (seção 3).
- **III. Separação de Domínio e Camadas** — `kafka/`, `avro/`, `registry/` são independentes de NiceGUI e FastAPI, consumidos por ambos via `services/`; verificado por `tests/test_architecture_boundaries.py`. ✅ respeitado (seção 3.2).
- **IV. Paridade UI/API (NFR-006)** — arquitetura em camadas com `services/` como ponto único de orquestração evita duplicação de lógica entre UI e API. ✅ respeitado, com uma exceção corrigida nesta revisão: a remoção de Configuração de Ambiente (FR-001) só existia via chamada direta a `config/manager.py` (TASK-008), sem UI/API — fechada por TASK-013b (rota `DELETE`) e TASK-014b (ação "Remover" na UI), ver achado G1 de `analysis.md`.
- **V. Segurança de Segredos Locais** — segredos de conexão ficam apenas no armazenamento local, nunca logados em texto claro. ✅ respeitado (seção 9, seção 11).

Nenhuma violação bloqueante identificada nesta revisão. Este check deve ser
reexecutado a cada emenda da constituição ou a cada `speckit-analyze`
subsequente.

---

## 3. Arquitetura

### 3.1 Visão geral

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
                          Registry)      serializer.py
        │                    │                │
        └────────────────────┴────────────────┘
                         │
              config/ (manager.py, models.py)
                         │
                 armazenamento local
           (arquivos JSON de configuração,
            .avsc carregados, log diário de operações)
```

`ui/` e `api/` são as **únicas** camadas que conhecem NiceGUI/FastAPI
respectivamente; ambas chamam exclusivamente `services/kafka_service.py`,
que é o único ponto que orquestra validação → serialização → Schema
Registry → publicação. Isso é o que garante NFR-006 (paridade UI/API) sem
duplicar lógica.

### 3.2 Estrutura de diretórios (herdada do briefing, mantida como está)

```text
app/
├── main.py                  # bootstrap: sobe NiceGUI + monta FastAPI no mesmo processo
│
├── ui/
│   ├── pages/                # Dashboard, Configurações (Kafka/Schema Registry),
│   │                         # Schemas Avro, Publicar Mensagem, API (redirect /docs), Logs
│   └── components/           # editor JSON, formulário auto-gerado, upload de arquivo
│
├── api/
│   ├── routes/                # health, configurations, schema, messages
│   └── schemas/                # modelos Pydantic de request/response (contratos HTTP)
│
├── kafka/
│   ├── connection.py           # factory de client Kafka (producer/admin) a partir de uma Configuração de Ambiente
│   ├── producer.py             # produção + espera de delivery report (partição/offset)
│   └── serializer.py           # serialização Avro binária (com ou sem Schema Registry)
│
├── avro/
│   ├── schema_loader.py         # parse/validação estrutural de .avsc, extração de nome/namespace/campos
│   └── validator.py             # validação de payload JSON contra o schema (fastavro.validate + mensagens por campo)
│
├── registry/
│   └── client.py                 # cliente HTTP do Schema Registry: testar, listar subjects/versões, registrar/reaproveitar
│
├── config/
│   ├── models.py                  # Pydantic: Configuração de Ambiente (Kafka + Schema Registry)
│   └── manager.py                  # CRUD de configurações em arquivo local, unicidade de nome
│
└── services/
    └── kafka_service.py            # orquestração: valida payload → serializa → (Schema Registry) → publica → registra operação

tests/
Dockerfile
docker-compose.yml
requirements.txt
README.md
.env.example
```

### 3.3 Fluxo principal (UI)

```text
Payload → Validação Avro → Serialização Avro → Schema Registry (se configurado) → Kafka
```

### 3.4 Fluxo de automação (API)

```text
Script/Automação --HTTP--> KafkaForge API (FastAPI, localhost) --> services/kafka_service.py --> Kafka
```

Mesmo `kafka_service.py` dos dois fluxos — não há um segundo caminho de
código para a API.

---

## 4. Componentes Afetados por User Story

| Story | Resumo | Componentes principais afetados |
|---|---|---|
| US-001a | Salvar e reabrir configuração Kafka | `config/models.py`, `config/manager.py`, `ui/pages/configuracoes_kafka.py`, `api/schemas/configurations.py` |
| US-001b | Testar configuração Kafka salva | `kafka/connection.py`, `services/kafka_service.py` (test_connection), `ui/pages/configuracoes_kafka.py`, `api/routes/configurations.py` (`POST /configurations/{name}/test`), exceções `KafkaConnectionError`/`KafkaAuthenticationError` |
| US-002a | Carregar/validar `.avsc` com tipos simples | `avro/schema_loader.py`, `ui/pages/schemas_avro.py`, `api/routes/schema.py` (`POST /schema/validate`), exceção `AvroSchemaError` |
| US-002b | Exibir tipos complexos do schema (union/enum/array/map/record) | `avro/schema_loader.py` (formatador recursivo de tipos), `ui/components/` (renderização de tipo composto) |
| US-003a | Validar payload contra schema | `avro/validator.py`, `services/kafka_service.py` (validate_payload), `ui/pages/publicar_mensagem.py`, `api/routes/messages.py` (`POST /messages/validate`), exceção `AvroValidationError` |
| US-003b | Publicar mensagem validada | `kafka/serializer.py`, `kafka/producer.py`, `services/kafka_service.py` (publish), `ui/pages/publicar_mensagem.py`, `api/routes/messages.py` (`POST /messages`), exceções `MessageSerializationError`/`MessagePublishError` |
| US-004a | Publicar via serviço local (automação) | `api/routes/messages.py`, `api/schemas/messages.py`, `services/kafka_service.py` (mesmo caminho de US-003b) |
| US-004b | Documentação interativa do serviço | `main.py` (montagem do FastAPI com `docs_url=/docs`), `api/routes/*` (docstrings/`response_model` para o OpenAPI gerado) |
| US-005a | Configurar/testar Schema Registry | `config/models.py` (bloco Schema Registry), `registry/client.py` (test), `ui/pages/configuracoes_schema_registry.py`, `api/routes/configurations.py`, exceção `SchemaRegistryError` |
| US-005b | Consultar/reaproveitar schemas do Schema Registry | `registry/client.py` (listar subjects/versões, registrar/checar existência), `ui/pages/schemas_avro.py` (seletor de subject), `kafka/serializer.py` (uso do schema id retornado) |
| US-006 | Múltiplas configurações de ambiente | `config/manager.py` (unicidade de nome, isolamento entre registros), `ui/components/` (seletor de ambiente reutilizado em Publicar/Testar) |
| US-007a | Status na tela inicial (Dashboard) | `services/kafka_service.py` (estado agregado: última conexão testada, contagem de schemas, última publicação), `ui/pages/dashboard.py` |
| US-007b | Histórico de operações | `services/kafka_service.py` (registro de cada operação), módulo de log estruturado (arquivo JSON diário — ver seção 10), `ui/pages/logs.py`, `api/routes` (opcional: exposição do histórico) |

Observação de sequenciamento: US-001a precede US-001b; US-003a precede
US-003b; US-004a e US-004b são independentes entre si mas dependem de
US-003b; US-005a precede US-005b; US-007a e US-007b dependem
transitivamente de praticamente todas as demais, pois consomem os eventos
que elas produzem.

---

## 5. Modelo de Dados

### Configuração de Ambiente (`config/models.py`)

| Campo | Tipo | Observações |
|---|---|---|
| `nome` | string | identificador único (US-006, edge case de nomes duplicados) |
| `kafka.bootstrap_servers` | string | lista de brokers |
| `kafka.security_protocol` | enum | `PLAINTEXT`, `SSL`, `SASL_PLAINTEXT`, `SASL_SSL` |
| `kafka.sasl_mechanism` | enum, opcional | ver decisão Q5 (seção 8) — apenas `PLAIN` nesta etapa |
| `kafka.username` / `kafka.password` | string, opcionais | autenticação usuário/senha |
| `kafka.ca_cert` / `kafka.client_cert` / `kafka.client_key` / `kafka.client_key_password` | arquivo/string, opcionais | mTLS; `client_key_password` opcional mesmo quando a chave a exige — validado apenas no teste de conexão (US-001b, cenário 3) |
| `schema_registry` | objeto opcional | `url`, `username`, `password`, `ca_cert`, `client_cert`, `client_key` — independente do bloco Kafka (FR-005) |

### Schema Avro

| Campo | Tipo |
|---|---|
| `nome`, `namespace` | string |
| `campos` | lista de `{nome, tipo}`, com `tipo` podendo ser primitivo ou composto (union/enum/array/map/record) |
| `conteudo_original` | string (JSON bruto do `.avsc`) |
| `origem` | `arquivo_local` \| `schema_registry` |
| `estado` | `válido` \| `inválido` (+ motivo) |

### Payload

| Campo | Tipo |
|---|---|
| `conteudo` | JSON |
| `schema_associado` | referência ao Schema Avro |
| `estado_validacao` | `válido` \| `inválido` |
| `problemas` | lista de `{campo, tipo_esperado, tipo_recebido}` quando inválido |

### Registro de Operação (`services/kafka_service.py` → log diário)

| Campo | Tipo |
|---|---|
| `timestamp` | datetime |
| `tipo_operacao` | `teste_conexao` \| `teste_schema_registry` \| `validacao_schema` \| `validacao_payload` \| `publicacao` |
| `configuracao` | nome da Configuração de Ambiente |
| `topic`, `schema`, `partition`, `offset` | quando aplicável |
| `chave` (key) | opcional — ver decisão Q1 |
| `resultado` | `sucesso` \| `erro` |
| `duracao_ms` | inteiro |
| `erro_tecnico` | string, quando `resultado = erro` |

Relações: uma Configuração de Ambiente é referenciada por N Registros de
Operação; um Schema Avro é referenciado por N Payloads e N Registros de
Operação. Nenhuma entidade tem ciclo de vida dependente de banco de dados —
tudo serializável em JSON.

---

## 6. Contratos de Interface

### 6.1 API REST local (FastAPI, `api/routes/`)

| Método | Rota | Story | Descrição |
|---|---|---|---|
| GET | `/api/v1/health` | US-004a | estado do serviço |
| GET | `/api/v1/configurations` | US-001a, US-006 | lista configurações salvas |
| POST | `/api/v1/configurations` | US-001a | cria/atualiza uma configuração |
| DELETE | `/api/v1/configurations/{name}` | US-001a | remove uma configuração salva (fecha lacuna G1 de `analysis.md`) |
| POST | `/api/v1/configurations/{name}/test` | US-001b | testa conexão Kafka (e, se aplicável, Schema Registry — US-005a) sem publicar nada |
| POST | `/api/v1/schema/validate` | US-002a, US-002b | valida um `.avsc` enviado, retorna nome/namespace/campos/tipos |
| POST | `/api/v1/messages/validate` | US-003a | valida um payload contra um schema, sem publicar |
| POST | `/api/v1/messages` | US-003b, US-004a | fluxo completo: valida → serializa → (Schema Registry) → publica |

**Contrato de `POST /api/v1/messages`** (referência: briefing, seção API REST):

Request:
```json
{
  "configuration": "desenvolvimento",
  "topic": "pedido-criado",
  "schema": "Pedido",
  "key": "opcional",
  "payload": { "id": 123, "cliente": "João", "valor": 199.90 }
}
```

Response (sucesso):
```json
{ "success": true, "topic": "pedido-criado", "partition": 2, "offset": 12345 }
```

Response (erro):
```json
{ "success": false, "error": "Mensagem incompatível com o schema Avro" }
```

`key` é opcional (decisão Q1, seção 8) — quando ausente, a publicação usa o
particionador padrão do Kafka; não há suporte a informar partição destino
explicitamente.

Todas as rotas usam `response_model` Pydantic para que a documentação
interativa (`/docs`, Swagger/OpenAPI — US-004b) seja gerada automaticamente
pelo FastAPI sem manutenção manual.

### 6.2 Páginas NiceGUI (`ui/pages/`)

| Página | Story | Elementos-chave |
|---|---|---|
| Dashboard | US-007a | status Kafka, status Schema Registry, configuração ativa, contagem de schemas, última mensagem publicada |
| Configurações → Kafka | US-001a, US-001b, US-006 | formulário de conexão, upload de certificados, botão "Testar conexão", lista/seleção/remoção de configurações nomeadas |
| Configurações → Schema Registry | US-005a | formulário de URL/credenciais/certificados, botão "Testar Schema Registry" |
| Schemas Avro | US-002a, US-002b, US-005b | upload `.avsc`, exibição de nome/namespace/campos/tipos, conteúdo original, seletor de subject do Schema Registry |
| Publicar Mensagem | US-003a, US-003b | seleção de configuração/tópico/schema, editor JSON (+ formulário auto-gerado, FR-012), botões "Validar" e "Publicar", exibição de partição/offset ou erro |
| API | US-004b | link/iframe para `/docs` |
| Logs | US-007b | tabela do histórico de operações com filtro por resultado/tipo |

### 6.3 Documentação interativa (US-004b)

FastAPI expõe `/docs` (Swagger UI) e `/openapi.json` automaticamente a
partir dos `response_model`/tipos de rota — sem trabalho adicional de
documentação manual, satisfazendo FR-022 "de graça".

---

## 7. Decisões Técnicas Resolvidas (Phase 0 — pesquisa consolidada)

Decisões já fechadas em `clarification.md`; registradas aqui no formato
Decision/Rationale/Alternativas para rastreabilidade arquitetural.

**Q1 — Chave e partição na publicação**
- Decision: suportar `key` (opcional) na publicação; **não** suportar seleção explícita de partição.
- Rationale: cobre o caso comum de particionamento por chave sem expor complexidade de administração de partições ao desenvolvedor.
- Alternativas consideradas: permitir partição explícita (rejeitado — exigiria expor semântica de admin client incompatível com "ferramenta simples"); exigir key obrigatória (rejeitado — nem todo tópico particiona por chave).

**Q2 — Timeout de operações**
- Decision: 10 segundos para "testar conexão", "testar Schema Registry" e "publicar".
- Rationale: valor único e previsível, simples de configurar em `confluent-kafka` (`socket.timeout.ms`/`message.timeout.ms`) e no cliente HTTP do Schema Registry, atende NFR-004.
- Alternativas consideradas: timeouts diferenciados por operação (rejeitado por ora — complexidade desnecessária); timeout configurável pelo usuário (não pedido, pode ser um refinamento futuro).

**Q3 — Binding do serviço local**
- Decision: bind exclusivo em `localhost`/`127.0.0.1`.
- Rationale: reforça NFR-001 (nada sai da máquina do desenvolvedor) sem depender de firewall externo; elimina superfície de exposição de credenciais na rede local.
- Alternativas consideradas: bind configurável em `0.0.0.0` (rejeitado — fora do escopo atual e contraria a premissa de ferramenta estritamente local).

**Q4 — Retenção do histórico de operações**
- Decision: histórico ilimitado, persistido em arquivo JSON tipo log, com um arquivo novo criado por dia (rotação diária).
- Rationale: evita banco de dados (restrição do briefing/NFR-005) mantendo histórico consultável e auditável por dia sem crescer um único arquivo indefinidamente.
- Alternativas consideradas: histórico só em memória (rejeitado — não sobrevive a reinício, contraria FR-024/FR-025 na prática); SQLite (rejeitado — foge da restrição explícita "sem banco de dados").
- Implicação de design: `services/kafka_service.py` escreve um registro por operação em `logs/operacoes-AAAA-MM-DD.json` (ou `.jsonl`); a tela de Logs (US-007b) e o Dashboard (US-007a) leem o(s) arquivo(s) mais recente(s) sem necessidade de índice.

**Q5 — Mecanismos SASL suportados**
- Decision: apenas usuário/senha (mecanismo `PLAIN`) nesta etapa; `SCRAM-SHA-256`/`SCRAM-SHA-512`/Kerberos ficam fora do escopo até serem pedidos explicitamente.
- Rationale: reduz a superfície de configuração e de testes na primeira entrega, mantendo o campo `sasl_mechanism` como enum extensível em `config/models.py` para adicionar mecanismos depois sem redesenho.
- Alternativas consideradas: suportar todos os mecanismos listados no briefing desde já (rejeitado pelo usuário — adiado deliberadamente).

---

## 8. Tratamento de Erros e Exceções

Hierarquia de exceções de domínio (todas em um módulo comum, ex.:
`app/exceptions.py`, consumidas por `kafka/`, `avro/`, `registry/` e
traduzidas por `services/kafka_service.py` em respostas compreensíveis
tanto para `ui/` quanto para `api/`):

```text
KafkaConnectionError
KafkaAuthenticationError
KafkaAuthorizationError
SchemaRegistryError
AvroSchemaError
AvroValidationError
MessageSerializationError
MessagePublishError
```

Regra única de apresentação (FR-026): cada exceção carrega uma mensagem
compreensível para o desenvolvedor (ex.: lista de itens a verificar) **e**
um detalhe técnico bruto, que vai para o Registro de Operação (seção 5) e
fica disponível na tela de Logs — nunca só um dos dois.

Caso de borda relevante para `config/manager.py` e `kafka/connection.py`:
certificado de cliente sem senha de chave privada quando a chave exige
senha deve estourar `KafkaAuthenticationError` com mensagem específica
apontando esse campo (US-001b, cenário 3) — não um erro genérico de SSL.

---

## 9. Persistência e Configuração Local

Sem banco de dados (NFR-005). Estrutura de armazenamento local proposta:

```text
~/.kafkaforge/                    (ou diretório configurável via .env)
├── configurations.json           # lista de Configurações de Ambiente (US-001a, US-006)
├── schemas/                      # .avsc carregados (cache local; US-002a/b)
└── logs/
    ├── operacoes-2026-08-22.json
    ├── operacoes-2026-08-23.json
    └── ...
```

Credenciais e certificados ficam apenas nesse armazenamento local
(NFR-003) — sem integração com Vault ou gestor corporativo de segredos,
conforme "Out of Scope" da especificação.

---

## 10. Dependências

### 10.1 Bibliotecas Python (a fixar em `requirements.txt`)

- `nicegui` — interface web
- `fastapi` + `uvicorn` — serviço local/API REST
- `confluent-kafka` (com extra `schema-registry`) — producer Kafka + cliente Schema Registry, suporte nativo a SSL/SASL
- `fastavro` — parse, validação estrutural e serialização binária Avro
- `pydantic` — modelos de configuração e contratos de API

### 10.2 Sistemas externos (fora do controle da aplicação)

- **Kafka corporativo**: alcançável via rede do desenvolvedor (VPN ou equivalente); a ferramenta não resolve problemas de conectividade de rede, apenas reporta falhas (assumption da spec).
- **Schema Registry corporativo** (opcional por ambiente): API compatível com o protocolo Confluent Schema Registry (subjects/versions).

### 10.3 Dependências entre stories

```text
US-001a ──▶ US-001b ──▶ US-007a
US-002a ──▶ US-002b
US-001b + US-002a ──▶ US-003a ──▶ US-003b ──▶ US-004a ──▶ US-004b
US-005a ──▶ US-005b
US-001a ──▶ US-006
(US-001b, US-002a, US-003a, US-003b, US-005a) ──▶ US-007b
```

### 10.4 Infraestrutura de empacotamento

Dockerfile + docker-compose.yml, subindo por padrão só a aplicação
(Kafka/Schema Registry locais em Docker são opcionais, só para
desenvolvimento/testes de integração — nunca obrigatórios para uso contra
o Kafka corporativo real).

---

## 11. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| `confluent-kafka` depende de `librdkafka` (extensão nativa C); instalação pode falhar em algumas máquinas/SOs sem toolchain de build | Bloqueia instalação da ferramenta (fere NFR-005 "simples de instalar") | Documentar no README pré-requisitos por SO; considerar wheels pré-compilados oficiais do `confluent-kafka` |
| mTLS com senha de chave privada opcional (Q1 de clarify) pode mascarar erro de configuração real como falha de "conexão" genérica | Mensagem de erro pouco acionável para o desenvolvedor (fere FR-026) | Validação específica no fluxo de teste de conexão: detectar chave protegida por senha ausente antes de tentar o handshake TLS e emitir `KafkaAuthenticationError` dedicado |
| Timeout único de 10s (Q2) pode ser curto demais para brokers corporativos atrás de VPN com latência alta | Falsos negativos em "testar conexão"/"publicar" | Deixar o valor centralizado em uma única constante de configuração, fácil de ajustar depois; medir com o Kafka corporativo real cedo no desenvolvimento |
| Log diário ilimitado (Q4) pode crescer indefinidamente em uso intenso de longa duração | Consumo de disco não controlado ao longo de meses | Fora de escopo tratar agora (decisão explícita do usuário); registrar como possível trabalho futuro (rotação/retenção configurável) |
| Divergência de comportamento entre UI e API se a lógica não passar 100% por `services/kafka_service.py` | Quebra NFR-006 (paridade UI/API) e SC-005 | Proibir, por convenção de arquitetura, que `ui/` ou `api/` chamem `kafka/`, `avro/` ou `registry/` diretamente — sempre via `services/` |
| Reaproveitamento de schema idêntico no Schema Registry (US-005b) exige comparação de conteúdo, não só de nome de subject | Duplicação de versões de schema (viola FR-015/SC-008) | Usar o endpoint nativo do Schema Registry para checar compatibilidade/existência de schema idêntico antes de registrar, em vez de comparação local ingênua |
| Uso simultâneo de UI e API sobre a mesma Configuração de Ambiente (edge case da spec) | Condição de corrida ao editar configuração enquanto uma publicação está em andamento | Leitura da Configuração de Ambiente feita uma vez por operação (snapshot), não por referência mutável compartilhada entre requisições |
| Certificados/segredos gravados em texto plano no armazenamento local | Exposição caso a máquina do desenvolvedor seja comprometida | Aceito conscientemente pela spec (NFR-003, sem gestor corporativo de segredos) — mitigar apenas com permissões de arquivo restritas (ex.: `0600`) no diretório `~/.kafkaforge/` |

---

## 12. Estratégia de Testes

Alinhada à seção "Testes" do briefing e aos critérios de aceite de cada
story:

- **Unitários**: `avro/schema_loader.py` (schemas válidos/inválidos, tipos simples e compostos — US-002a/b), `avro/validator.py` (payload válido, tipo incompatível, union opcional nula, campos extras/ausentes — US-003a), `config/manager.py` (unicidade de nome, isolamento entre configurações — US-006).
- **Integração** (Kafka e Schema Registry via Docker, quando disponíveis): `kafka/connection.py` (SSL, SASL/PLAIN — US-001b), `kafka/producer.py` + `kafka/serializer.py` (publicação de ponta a ponta — US-003b), `registry/client.py` (teste de conectividade, listagem de subjects, reaproveitamento de schema idêntico — US-005a/b).
- **API**: cada rota de `api/routes/` testada com `TestClient` do FastAPI, incluindo os casos de erro (configuração/schema inexistentes — US-004a) e a paridade de resultado com o fluxo de UI (NFR-006).
- **Fora de escopo automatizar**: qualquer teste que dependa de um Kafka corporativo real — esses ficam como roteiro manual de validação (quickstart), não como suíte de CI.

---

## 13. Fases de Implementação Sugeridas

Sequenciamento por prioridade da especificação (P1 → P2 → P3), respeitando
as dependências da seção 10.3:

1. **Fase 1 (P1 — fluxo mínimo fim-a-fim)**: US-001a, US-001b, US-002a,
   US-002b, US-003a, US-003b, US-004a, US-004b. Entrega o resultado
   esperado central do briefing: configurar Kafka, carregar `.avsc`,
   validar e publicar, tanto pela tela quanto pela API.
2. **Fase 2 (P2 — Schema Registry e múltiplos ambientes)**: US-005a,
   US-005b, US-006. Adiciona reaproveitamento de schemas e uso realista
   contra vários ambientes corporativos.
3. **Fase 3 (P3 — observabilidade local)**: US-007a, US-007b. Fecha o
   ciclo de troubleshooting sem exigir leitura de código-fonte (SC-007).

---

## 14. Validação de Ponta a Ponta (roteiro de referência)

1. Subir a aplicação localmente (`docker-compose up` ou execução direta).
2. Cadastrar uma Configuração de Ambiente ("Desenvolvimento") com um Kafka
   acessível (US-001a) e acionar "Testar conexão" (US-001b).
3. Fazer upload de um `.avsc` de exemplo com tipos simples e compostos
   (US-002a/b) e conferir nome/namespace/campos exibidos.
4. Montar um payload compatível no editor JSON, validar (US-003a) e
   publicar (US-003b); conferir tópico/partição/offset exibidos.
5. Repetir o passo 4 via `curl` contra `POST /api/v1/messages` (US-004a) e
   comparar o resultado com o obtido pela tela (SC-005); consultar `/docs`
   (US-004b).
6. Abrir o Dashboard (US-007a) e a tela de Logs (US-007b) e confirmar que
   refletem as operações realizadas nos passos anteriores.

---

## 15. Questões em Aberto

Nenhuma. Todos os pontos que estavam marcados como
`NEEDS CLARIFICATION` na especificação foram resolvidos em
`clarification.md` (Q1–Q5) e incorporados como decisões de arquitetura na
seção 8.

---

## Extension Hooks (pós-plano)

Nenhum hook encontrado: `.specify/extensions.yml` não existe. Etapa
ignorada.

---

## Relatório de Conclusão

- **Branch**: não aplicável — diretório de trabalho não é um repositório Git.
- **Plano**: `.squad/features/001/plan.md` (este arquivo).
- **Artefatos gerados**: consolidados neste único documento (contexto
  técnico, constitution check, arquitetura, componentes por story, modelo
  de dados, contratos de API/UI, decisões técnicas equivalentes a
  `research.md`, riscos, estratégia de testes, fases e roteiro de
  validação de ponta a ponta equivalente a `quickstart.md`), dado que o
  projeto não possui o scaffold `.specify/` para gerar arquivos separados.
