---
stage: tasks
status: approved
sourceSkill:
  id: speckit-tasks
  version: 7ccbc52570135b6455b4973161757a91cf01d8630f457aa662294a7d37f9a40d
implementSessionId: bd1d52b7-1cfd-4f9f-8aea-eb2773d646c4
implementedTaskIds:
  - TASK-001
  - TASK-002
  - TASK-003
  - TASK-004
  - TASK-005
  - TASK-006
  - TASK-007
  - TASK-008
  - TASK-009
  - TASK-010
  - TASK-011
  - TASK-012
  - TASK-013
  - TASK-014
  - TASK-015
  - TASK-016
  - TASK-013b
  - TASK-014b
  - TASK-017
  - TASK-018
  - TASK-019
  - TASK-020
  - TASK-021
  - TASK-022
  - TASK-023
  - TASK-024
  - TASK-025
  - TASK-026
  - TASK-027
  - TASK-028
  - TASK-029
---

# Tasks: KafkaForge — Envio de Mensagens Avro para o Kafka Corporativo

**Feature**: 001
**Diretório**: `.squad/features/001`
**Plano**: `.squad/features/001/plan.md`
**Especificação**: `.squad/features/001/spec.md`
**Stories**: `.squad/features/001/stories/US-001a.md` … `.squad/features/001/stories/US-007b.md`
**Criado em**: 2026-08-22
**Status**: Draft

> Este repositório não possui o scaffold `.specify/` (sem `setup-tasks.sh` nem
> template de tasks). Esta decomposição foi montada diretamente sobre o
> Plano Técnico aprovado (`plan.md`), seguindo o mesmo sequenciamento de fases
> (Setup → Fundação → Stories em ordem de prioridade P1/P2/P3 → Polimento)
> descrito na seção 13 do plano.

## Extension Hooks

Nenhum hook encontrado: `.specify/extensions.yml` não existe no diretório do
projeto. Etapas de hooks (pré e pós-tasks) ignoradas silenciosamente.

---

## Resumo das Fases

1. **Fase 1 — Setup**: TASK-001 a TASK-006. Estrutura de projeto, dependências, empacotamento e armazenamento local.
2. **Fase 2 — Fundação**: TASK-007 a TASK-011. Bloqueante para todas as stories: modelo de Configuração de Ambiente, `services/kafka_service.py`, log de operações, esqueleto da API.
3. **Fase 3 — Stories P1 (fluxo mínimo fim-a-fim)**: US-001a, US-001b, US-002a, US-002b, US-003a, US-003b, US-004a, US-004b — TASK-012 a TASK-042.
4. **Fase 4 — Stories P2 (Schema Registry e múltiplos ambientes)**: US-005a, US-005b, US-006 — TASK-043 a TASK-052.
5. **Fase 5 — Stories P3 (observabilidade local)**: US-007a, US-007b — TASK-053 a TASK-057.
6. **Fase 6 — Polimento e cross-cutting**: TASK-058 a TASK-064.

Dependências entre stories (herdadas do plano, seção 10.3):

```text
US-001a ──▶ US-001b ──▶ US-007a
US-002a ──▶ US-002b
US-001b + US-002a ──▶ US-003a ──▶ US-003b ──▶ US-004a ──▶ US-004b
US-005a ──▶ US-005b
US-001a ──▶ US-006
(US-001b, US-002a, US-003a, US-003b, US-005a) ──▶ US-007b
```

**MVP sugerido**: Fase 1 + Fase 2 + Fase 3 (US-001a até US-004b) entrega o
resultado central do briefing — configurar Kafka, carregar `.avsc`, validar e
publicar, tanto pela tela quanto pela API.

---

### Fase 1: Setup

## TASK-001 [X]
Criar a estrutura de diretórios do projeto conforme a seção 3.2 do plano:
`app/main.py`, `app/ui/pages/`, `app/ui/components/`, `app/api/routes/`,
`app/api/schemas/`, `app/kafka/`, `app/avro/`, `app/registry/`,
`app/config/`, `app/services/`, `tests/`, `Dockerfile`,
`docker-compose.yml`, `requirements.txt`, `README.md`, `.env.example`.

Story: N/A (tarefa de infraestrutura, base para todas as stories)

Definition of Done:
- Todos os diretórios e arquivos vazios/placeholder listados existem no repositório.
- A estrutura corresponde exatamente à árvore descrita na seção 3.2 do `plan.md`.
- Nenhuma lógica de negócio foi escrita nesta tarefa (apenas esqueleto).

## TASK-002 [X]
Criar `requirements.txt` fixando as bibliotecas Python definidas na seção
10.1 do plano: `nicegui`, `fastapi`, `uvicorn`, `confluent-kafka` (com o
extra `schema-registry`), `fastavro`, `pydantic`.

Story: N/A (tarefa de infraestrutura)

Definition of Done:
- `requirements.txt` lista todas as bibliotecas com versões fixadas (pinned).
- `pip install -r requirements.txt` é executado com sucesso em um ambiente limpo.
- README documenta pré-requisitos de SO para compilar `confluent-kafka`/`librdkafka` (referenciado também em TASK-062).

## TASK-003 [X]
Criar `Dockerfile` e `docker-compose.yml` conforme seção 10.4 do plano:
imagem da aplicação KafkaForge, subindo por padrão apenas a aplicação
(Kafka/Schema Registry locais em Docker ficam como serviços opcionais,
comentados ou em profile separado, só para desenvolvimento/testes).

Story: N/A (tarefa de infraestrutura)

Definition of Done:
- `docker-compose up` sobe somente o serviço da aplicação por padrão.
- Existe um profile ou serviço comentado para subir Kafka/Schema Registry locais opcionalmente.
- A imagem construída expõe a porta usada pelo NiceGUI/FastAPI em `localhost`.

## TASK-004 [X]
Implementar `app/main.py` como bootstrap único do processo: sobe a interface
NiceGUI e monta o FastAPI no mesmo processo, com bind exclusivo em
`localhost`/`127.0.0.1` (decisão Q3, seção 7 do plano) e `docs_url="/docs"`
habilitado.

Story: N/A (tarefa de infraestrutura, pré-requisito de US-004b)

Definition of Done:
- A aplicação sobe com um único comando e serve tanto as páginas NiceGUI quanto as rotas FastAPI.
- O bind é feito exclusivamente em `127.0.0.1` — nenhuma tentativa de expor em `0.0.0.0`.
- `/docs` responde com o Swagger UI assim que houver ao menos a rota de health (TASK-011).

## TASK-005 [X]
Criar `app/exceptions.py` com a hierarquia base de exceções de domínio
descrita na seção 8 do plano (`KafkaConnectionError`,
`KafkaAuthenticationError`, `KafkaAuthorizationError`,
`SchemaRegistryError`, `AvroSchemaError`, `AvroValidationError`,
`MessageSerializationError`, `MessagePublishError`), cada uma carregando uma
mensagem compreensível e um detalhe técnico bruto (FR-026).

Story: N/A (tarefa de infraestrutura; consumida por todas as stories P1/P2)

Definition of Done:
- Cada classe de exceção aceita separadamente uma mensagem amigável e um detalhe técnico.
- As exceções estão organizadas em um único módulo, sem dependência de `ui/`, `api/`, `kafka/`, `avro/` ou `registry/`.
- Cobertura de teste unitário mínima garantindo que ambos os atributos (mensagem amigável e detalhe técnico) ficam acessíveis após a exceção ser capturada.

## TASK-006 [X]
Implementar a estrutura de armazenamento local descrita na seção 9 do
plano: diretório `~/.kafkaforge/` (ou caminho configurável via `.env`) com
`configurations.json`, `schemas/` e `logs/`, criado automaticamente na
primeira execução com permissões restritas (`0600`/`0700`) para proteger
credenciais e certificados (NFR-003, risco de segurança da seção 11).

Story: N/A (tarefa de infraestrutura, pré-requisito de US-001a e US-007b)

Definition of Done:
- Na primeira execução, `~/.kafkaforge/` (ou caminho de `.env`) é criado automaticamente se não existir.
- Arquivos e diretórios criados têm permissões restritas ao usuário dono do processo.
- O caminho base é configurável via variável de ambiente documentada em `.env.example`.

---

### Fase 2: Fundação (bloqueante para todas as stories)

## TASK-007 [X]
Implementar `app/config/models.py` com o modelo Pydantic de **Configuração
de Ambiente** descrito na seção 5 do plano: bloco Kafka (`bootstrap_servers`,
`security_protocol`, `sasl_mechanism` limitado a `PLAIN` por ora — decisão
Q5, credenciais usuário/senha, certificados mTLS incluindo
`client_key_password` opcional) e bloco `schema_registry` opcional e
independente do bloco Kafka (FR-005).

Story: N/A (fundação; pré-requisito direto de US-001a, US-005a e US-006)

Definition of Done:
- O modelo Pydantic valida todos os campos da tabela "Configuração de Ambiente" da seção 5 do plano.
- `sasl_mechanism` é um enum extensível contendo apenas `PLAIN` nesta etapa, sem quebrar ao adicionar novos valores depois.
- O bloco `schema_registry` pode estar totalmente ausente sem invalidar o restante da configuração.

## TASK-008 [X]
Implementar `app/config/manager.py` com CRUD de Configurações de Ambiente
persistidas em `configurations.json` (armazenamento local, seção 9),
incluindo validação de unicidade de nome (edge case da spec e cenário 4 de
US-006).

Story: N/A (fundação; pré-requisito direto de US-001a e US-006)

Definition of Done:
- Criar, listar, editar e remover uma Configuração de Ambiente funciona via chamadas diretas ao módulo, sem UI/API.
- Duas configurações com o mesmo nome não podem coexistir — a segunda tentativa é rejeitada com erro claro.
- Editar uma configuração não altera o conteúdo de nenhuma outra configuração salva.

## TASK-009 [X]
Criar o esqueleto de `app/services/kafka_service.py` como ponto único de
orquestração (arquitetura da seção 3.1 e 3.4 do plano), definindo as
assinaturas dos métodos que serão implementados nas fases seguintes
(`test_connection`, `test_schema_registry`, `validate_schema`,
`validate_payload`, `publish`) e a regra arquitetural de que `ui/` e `api/`
só podem chamar este módulo, nunca `kafka/`, `avro/` ou `registry/`
diretamente (mitigação de risco da seção 11, garantia de NFR-006).

Story: N/A (fundação; pré-requisito de todas as stories P1/P2/P3)

Definition of Done:
- O módulo expõe as assinaturas de todos os métodos de orquestração listados, mesmo que com implementação provisória.
- Existe um teste ou verificação (lint/import-check) que impede `ui/` e `api/` de importar `kafka/`, `avro/` ou `registry/` diretamente.
- A leitura da Configuração de Ambiente é feita por snapshot a cada chamada, não por referência mutável compartilhada (edge case de concorrência UI+API).

## TASK-010 [X]
Implementar o módulo de log estruturado de operações com rotação diária
(decisão Q4, seção 7): grava um registro por operação em
`logs/operacoes-AAAA-MM-DD.json` (ou `.jsonl`) seguindo o modelo "Registro
de Operação" da seção 5 do plano.

Story: N/A (fundação; pré-requisito direto de US-007a e US-007b)

Definition of Done:
- Cada chamada de gravação cria/anexa ao arquivo do dia corrente sem sobrescrever dias anteriores.
- O registro gravado contém todos os campos mínimos exigidos por FR-024 (timestamp, tipo de operação, configuração, tópico/schema quando aplicável, resultado, duração, erro técnico quando houver).
- A leitura do(s) arquivo(s) mais recente(s) não exige nenhum índice ou banco de dados.

## TASK-011 [X]
Implementar `app/api/routes/` com a rota `GET /api/v1/health` e o
mecanismo de registro de rotas em `main.py`, servindo de base para as
demais rotas da API (seção 6.1 do plano).

Story: N/A (fundação; pré-requisito direto de US-004a)

Definition of Done:
- `GET /api/v1/health` responde com o estado do serviço em `localhost`.
- A rota aparece automaticamente em `/docs` assim que `main.py` monta o FastAPI (TASK-004).
- Novas rotas podem ser registradas em `api/routes/` sem alterar `main.py` além de um único ponto de inclusão de router.

---

### Fase 3: User Stories P1 — fluxo mínimo fim-a-fim

## TASK-012 [X]
Implementar `app/api/schemas/configurations.py` com os modelos Pydantic de
request/response para criar e listar Configurações de Ambiente (contrato
HTTP da seção 6.1 do plano).

Story: US-001a

Definition of Done:
- Os modelos de request/response cobrem todos os campos da Configuração de Ambiente (seção 5 do plano).
- Os modelos são usados como `response_model`/tipo de corpo nas rotas de `api/routes/configurations.py`.
- Erros de validação de campo retornam mensagem compreensível (não apenas erro genérico do Pydantic sem contexto).

## TASK-013 [X]
Implementar `app/api/routes/configurations.py` com as rotas
`GET /api/v1/configurations` e `POST /api/v1/configurations`, usando
`config/manager.py` (TASK-008) via `services/kafka_service.py`.

Story: US-001a

Definition of Done:
- `POST /api/v1/configurations` salva uma nova configuração e ela pode ser reaberta em uma chamada `GET` subsequente (cenário 1 de US-001a).
- Tentar salvar um nome já existente retorna um erro claro, sem sobrescrever silenciosamente.
- A rota não chama `config/manager.py` diretamente — passa por `services/kafka_service.py`.

## TASK-013b [X]
Implementar em `app/api/routes/configurations.py` a rota
`DELETE /api/v1/configurations/{name}`, usando `config/manager.py`
(TASK-008) via `services/kafka_service.py`.

Story: US-001a

Definition of Done:
- `DELETE /api/v1/configurations/{name}` remove a configuração e uma chamada `GET` subsequente não a lista mais (fecha a lacuna de FR-001 identificada em `analysis.md`, achado G1).
- Remover uma configuração inexistente retorna um erro claro (404), sem afetar as demais configurações salvas.
- A rota não chama `config/manager.py` diretamente — passa por `services/kafka_service.py` (mesma regra de TASK-013).

## TASK-014 [X]
Implementar `app/ui/pages/configuracoes_kafka.py` com formulário de
criação/edição de Configuração de Ambiente (nome, brokers, protocolo de
segurança, credenciais, upload de certificados) e lista de configurações
salvas.

Story: US-001a

Definition of Done:
- Um desenvolvedor sem nenhuma configuração salva consegue preencher o formulário e salvar (cenário 1 do Acceptance Scenario de US-001a).
- A configuração salva aparece na lista e pode ser reaberta para edição.
- Upload de certificado por arquivo funciona (FR-003).

## TASK-014b [X]
Estender `app/ui/pages/configuracoes_kafka.py` com uma ação "Remover" na
lista de configurações salvas, com confirmação antes de excluir, chamando
`DELETE /api/v1/configurations/{name}` (TASK-013b) através de
`services/kafka_service.py`.

Story: US-001a

Definition of Done:
- Um desenvolvedor consegue remover uma configuração salva diretamente pela lista da tela (fecha a lacuna de FR-001 identificada em `analysis.md`, achado G1 — antes a remoção só existia via chamada direta ao módulo, TASK-008, sem UI/API).
- A remoção pede confirmação antes de executar, evitando exclusão acidental.
- Após remover, a configuração some da lista sem exigir recarregar a página manualmente, e o comportamento é equivalente ao da rota (TASK-013b), preservando NFR-006.

## TASK-015 [X]
Implementar `app/kafka/connection.py`: factory de client Kafka
(producer/admin) a partir de uma Configuração de Ambiente, com timeout de
10 segundos (decisão Q2) e suporte a SSL e SASL/PLAIN (decisão Q5).

Story: US-001b

Definition of Done:
- A factory constrói um client Kafka válido a partir de qualquer combinação suportada de `security_protocol`.
- O timeout de conexão é de 10 segundos, configurado em uma única constante reutilizável.
- Um certificado de cliente sem senha de chave privada, quando a chave exige senha, é detectado antes do handshake TLS.

## TASK-016 [X]
Estender `app/exceptions.py` com o comportamento específico de
`KafkaAuthenticationError` para o caso de certificado de cliente sem senha
de chave privada (cenário 3 de US-001b), apontando esse campo
especificamente em vez de um erro genérico de SSL.

Story: US-001b

Definition of Done:
- A mensagem amigável da exceção identifica explicitamente o campo de senha da chave privada ausente.
- Um teste unitário cobre esse cenário isoladamente, sem depender de um broker real.

## TASK-017 [X]
Implementar em `services/kafka_service.py` o método `test_connection`,
usando `kafka/connection.py` (TASK-015), garantindo ausência de efeitos
colaterais sobre o cluster (NFR-002 — não publica mensagens nem
registra/altera schemas).

Story: US-001b

Definition of Done:
- Uma conexão válida retorna sucesso sem que nenhuma mensagem seja publicada no tópico de teste.
- Uma conexão inválida (broker inexistente, credencial inválida, certificado incorreto) retorna falha com motivo compreensível (cenário 2 de US-001b).
- O resultado (sucesso/falha) é gravado como Registro de Operação via TASK-010.

## TASK-018 [X]
Implementar em `app/api/routes/configurations.py` a rota
`POST /api/v1/configurations/{name}/test`.

Story: US-001b

Definition of Done:
- A rota retorna sucesso ou falha compreensível chamando exclusivamente `services/kafka_service.py`.
- A rota está documentada com `response_model` e aparece em `/docs`.

## TASK-019 [X]
Estender `app/ui/pages/configuracoes_kafka.py` com o botão "Testar
conexão" e a exibição clara do resultado (sucesso ou falha com motivo).

Story: US-001b

Definition of Done:
- Acionar "Testar conexão" com uma configuração válida exibe sucesso sem publicar nada (cenário 1 do Acceptance Scenario de US-001b da spec).
- Acionar "Testar conexão" com dado incorreto exibe falha com mensagem compreensível (cenário 2).
- O resultado exibido na UI é visualmente equivalente ao retornado pela API (TASK-018), preservando NFR-006.

## TASK-020 [X]
Adicionar `AvroSchemaError` em `app/exceptions.py` para representar falhas
de estrutura de schema Avro.

Story: US-002a

Definition of Done:
- A exceção carrega mensagem compreensível e detalhe técnico bruto (FR-026).
- É usada exclusivamente por `avro/schema_loader.py`, sem duplicar lógica em `ui/` ou `api/`.

## TASK-021 [X]
Implementar `app/avro/schema_loader.py`: parse e validação estrutural de
arquivos `.avsc` com tipos simples, extraindo nome, namespace e lista de
campos com tipos.

Story: US-002a

Definition of Done:
- Um `.avsc` válido com tipos simples retorna nome, namespace, campos e tipos corretamente (cenário 1 do Acceptance Scenario de US-002a).
- Um `.avsc` com estrutura JSON inválida é rejeitado com mensagem compreensível (cenário 2).
- Um `.avsc` sintaticamente válido como JSON mas semanticamente inválido como Avro (tipo desconhecido, `record` incompleto) é rejeitado com explicação, sem travar nem ser aceito silenciosamente (cenário 3, edge case da spec).

## TASK-022 [X]
Implementar `app/api/routes/schema.py` com a rota
`POST /api/v1/schema/validate`.

Story: US-002a

Definition of Done:
- A rota aceita um `.avsc` e retorna nome/namespace/campos/tipos ou erro compreensível, via `services/kafka_service.py`.
- Casos de schema inválido retornam um erro estruturado, não um erro 500 genérico.

## TASK-023 [X]
Implementar `app/ui/pages/schemas_avro.py` (versão inicial): upload de
`.avsc`, exibição de nome, namespace, lista de campos com tipos e conteúdo
original do schema, com mensagem compreensível em caso de rejeição.

Story: US-002a

Definition of Done:
- Upload de um `.avsc` válido exibe nome, namespace, campos, tipos e conteúdo original (cenário 1 do Acceptance Scenario de US-002a).
- Upload de um `.avsc` inválido exibe explicação compreensível do problema, sem interromper o uso das demais telas (FR-009).

## TASK-024 [X]
Estender `app/avro/schema_loader.py` com um formatador recursivo de tipos
compostos (union, enum, array, map, record — incluindo campo opcional do
tipo `["null", "string"]`).

Story: US-002b

Definition of Done:
- Um schema contendo os cinco tipos compostos listados é carregado e todos os campos/tipos são exibidos corretamente (cenário único do Acceptance Scenario de US-002b).
- O campo opcional `["null", "string"]` é formatado de forma legível (não como union bruta ilegível).

## TASK-025 [X]
Implementar em `app/ui/components/` um componente de renderização de tipo
composto, reutilizado pela tela Schemas Avro para exibir union/enum/
array/map/record de forma legível.

Story: US-002b

Definition of Done:
- O componente exibe corretamente os cinco tipos compostos suportados (FR-010).
- O mesmo componente é reutilizado sem duplicação de lógica de formatação entre páginas.

## TASK-026 [X]
Adicionar `AvroValidationError` em `app/exceptions.py` para falhas de
validação de payload contra schema.

Story: US-003a

Definition of Done:
- A exceção carrega, no detalhe estruturado, o campo problemático, o tipo esperado e o tipo recebido (FR-013).

## TASK-027 [X]
Implementar `app/avro/validator.py`: validação de payload JSON contra um
Schema Avro usando `fastavro.validate` (ou equivalente), com mensagens de
erro por campo.

Story: US-003a

Definition of Done:
- Um payload compatível com o schema é confirmado como válido (cenário 1 do Acceptance Scenario de US-003a).
- Um payload com tipo incompatível (ex.: texto em campo numérico) aponta campo, tipo esperado e tipo recebido (cenário 2).
- Um campo opcional do tipo `["null", "string"]` aceita corretamente tanto ausência quanto o tipo alternativo (cenário 3, edge case da spec).
- Campos extras não previstos no schema e campos obrigatórios ausentes são ambos sinalizados como inválidos (cenário 4).

## TASK-028 [X]
Implementar em `services/kafka_service.py` o método `validate_payload`,
usando `avro/validator.py` (TASK-027).

Story: US-003a

Definition of Done:
- O método retorna estado de validação e lista de problemas por campo quando inválido.
- O resultado da validação é gravado como Registro de Operação via TASK-010.

## TASK-029 [X]
Implementar `app/api/routes/messages.py` com a rota
`POST /api/v1/messages/validate`.

Story: US-003a

Definition of Done:
- A rota valida um payload contra um schema e retorna o mesmo formato de erro (campo/tipo esperado/tipo recebido) usado pela UI.
- Nenhuma publicação no Kafka ocorre ao chamar esta rota.

## TASK-030 [X]
Implementar `app/ui/pages/publicar_mensagem.py` (versão inicial): seleção
de configuração/tópico/schema, editor JSON para o payload e botão
"Validar", exibindo o resultado da validação.

Story: US-003a

Definition of Done:
- Um payload válido é confirmado como válido ao clicar em "Validar" (FR-011, FR-013).
- Um payload inválido exibe o campo problemático, tipo esperado e tipo recebido diretamente na tela.
- O editor JSON é o mecanismo mínimo funcional desta tarefa; o formulário auto-gerado (FR-012) é entregue separadamente pela TASK-030b.

## TASK-030b [X]
Implementar em `app/ui/components/` um gerador de formulário que cria
automaticamente um campo por atributo do schema Avro selecionado (FR-012),
como alternativa ao editor JSON de `publicar_mensagem.py` (TASK-030) — ambos
preenchendo o mesmo payload.

Story: US-003a

Definition of Done:
- Ao selecionar um schema, o formulário exibe um campo por atributo, com o tipo de entrada apropriado ao tipo Avro do campo (texto, número, booleano etc.).
- Preencher o formulário e preencher o editor JSON produzem o mesmo payload, validável por `avro/validator.py` (TASK-027) — nenhuma lógica de validação é duplicada entre os dois caminhos.
- O editor JSON continua disponível e funcional como alternativa (FR-012 exige manter as duas opções, não substituir uma pela outra).
- Fecha a lacuna identificada em `analysis.md`, achado G2 (FR-012 sem tarefa própria).

## TASK-031 [X]
Adicionar `MessageSerializationError` e `MessagePublishError` em
`app/exceptions.py`.

Story: US-003b

Definition of Done:
- Ambas as exceções carregam mensagem compreensível e detalhe técnico bruto, distinguindo falha de serialização de falha de publicação no Kafka.

## TASK-032 [X]
Implementar `app/kafka/serializer.py`: serialização de payload no formato
Avro binário compatível com o schema selecionado, funcionando com ou sem
Schema Registry configurado.

Story: US-003b

Definition of Done:
- Um payload válido é serializado corretamente em Avro binário usando apenas o `.avsc` local, sem exigir Schema Registry (cenário 4 do Acceptance Scenario de US-003b, FR-014).
- Falha de serialização lança `MessageSerializationError` com detalhe técnico.

## TASK-033 [X]
Implementar `app/kafka/producer.py`: produção da mensagem serializada e
espera do delivery report (partição e offset), respeitando o timeout de
10 segundos (decisão Q2).

Story: US-003b

Definition of Done:
- Uma publicação bem-sucedida retorna partição e offset reais do broker (cenário 1 do Acceptance Scenario de US-003b, FR-017).
- Uma falha durante a publicação (tópico inexistente, perda de conexão) é reportada como erro claro, sem ser apresentada como sucesso sem confirmação do broker (cenário 2, edge case da spec).

## TASK-034 [X]
Implementar em `services/kafka_service.py` o método `publish`,
orquestrando validar → serializar → (Schema Registry, se configurado) →
publicar → registrar operação, usando os módulos das TASK-027, TASK-032 e
TASK-033.

Story: US-003b

Definition of Done:
- Um payload inválido é bloqueado antes de qualquer tentativa de publicação no Kafka (cenário 3 do Acceptance Scenario de US-003b, FR-013).
- Toda publicação (sucesso ou falha) gera um Registro de Operação via TASK-010.
- Este é o único caminho de código usado tanto pela UI quanto pela API para publicar mensagens (NFR-006).

## TASK-035 [X]
Implementar em `app/api/routes/messages.py` a rota `POST /api/v1/messages`.

Story: US-003b

Definition of Done:
- A rota retorna tópico, partição e offset em caso de sucesso, ou erro compreensível em caso de falha (contrato da seção 6.1 do plano).
- O resultado é equivalente ao obtido publicando a mesma mensagem pela UI (SC-005), usando o mesmo `services/kafka_service.py`.

## TASK-036 [X]
Estender `app/ui/pages/publicar_mensagem.py` com o botão "Publicar" e a
exibição de tópico/partição/offset em caso de sucesso, ou mensagem de erro
em caso de falha.

Story: US-003b

Definition of Done:
- Uma publicação bem-sucedida exibe tópico, partição e offset diretamente na tela (SC-004, cenário 1 do Acceptance Scenario de US-003b).
- Uma falha de publicação exibe uma indicação clara de falha com a mensagem de erro correspondente (cenário 2, FR-018).

## TASK-037 [X]
Implementar `app/api/schemas/messages.py` com os modelos Pydantic de
request/response de `POST /api/v1/messages` (`configuration`, `topic`,
`schema`, `key` opcional, `payload`), conforme contrato da seção 6.1 do
plano.

Story: US-004a

Definition of Done:
- O modelo de request aceita `key` como campo opcional (decisão Q1) sem exigir seleção explícita de partição.
- O modelo de response cobre tanto o formato de sucesso (`success`, `topic`, `partition`, `offset`) quanto o de erro (`success: false`, `error`).

## TASK-038 [X]
Estender `app/api/routes/messages.py` para tratar, de forma compreensível,
os casos de configuração ou schema inexistentes informados por uma
automação externa.

Story: US-004a

Definition of Done:
- Uma requisição com configuração ou schema inexistente retorna um erro indicando especificamente qual dos dois não foi encontrado (cenário 3 do Acceptance Scenario de US-004a).
- Uma requisição com payload incompatível é recusada sem tentar publicar no Kafka (cenário 2).
- Uma requisição válida retorna tópico, partição e offset (cenário 1), com resultado equivalente ao obtido pela tela (SC-005).

## TASK-039 [X]
Validar/estender `GET /api/v1/health` (TASK-011) para refletir o estado
atual do serviço local, consumível por uma automação antes de tentar
publicar.

Story: US-004a

Definition of Done:
- A rota responde de forma consistente mesmo sem nenhuma configuração cadastrada ainda.
- O tempo de resposta é curto e previsível (NFR-004).

## TASK-040 [X]
Confirmar/ajustar em `app/main.py` a montagem do FastAPI com
`docs_url="/docs"` e `/openapi.json` habilitados (complementa TASK-004
agora que existem rotas reais de configuração, schema e mensagens).

Story: US-004b

Definition of Done:
- `/docs` lista todas as rotas implementadas até esta fase (health, configurations, schema, messages).
- Um desenvolvedor consegue testar cada operação diretamente pelo Swagger UI, sem cliente HTTP externo (cenário único do Acceptance Scenario de US-004b).

## TASK-041 [X]
Revisar `app/api/routes/*` garantindo `response_model`, docstrings e
exemplos de request/response em todas as rotas, para que a documentação em
`/docs` seja gerada automaticamente sem manutenção manual (FR-022).

Story: US-004b

Definition of Done:
- Todas as rotas de `configurations`, `schema` e `messages` têm `response_model` definido.
- A documentação gerada em `/docs` permite entender o propósito de cada rota sem ler o código-fonte (SC-007 aplicado à API).

## TASK-042 [X]
Implementar a página "API" em `ui/pages/` com link/iframe para `/docs`.

Story: US-004b

Definition of Done:
- A página é acessível a partir da navegação principal da UI.
- O link/iframe aponta corretamente para `/docs` no mesmo processo local.

---

### Fase 4: User Stories P2 — Schema Registry e múltiplos ambientes

## TASK-043 [X]
Estender `app/config/models.py` (TASK-007) garantindo que o bloco
`schema_registry` (url, username, password, ca_cert, client_cert,
client_key) seja totalmente independente do bloco Kafka (FR-005), incluindo
o caso de ausência completa do bloco para um ambiente.

Story: US-005a

Definition of Done:
- Uma Configuração de Ambiente pode existir com bloco Kafka preenchido e `schema_registry` ausente, sem erro de validação.
- Publicar/validar mensagens sem Schema Registry continua funcionando via `.avsc` local (FR-007, cenário 4 do Acceptance Scenario de US-003b).

## TASK-044 [X]
Adicionar `SchemaRegistryError` em `app/exceptions.py`.

Story: US-005a

Definition of Done:
- A exceção distingue claramente falha de Schema Registry de falha de conexão Kafka (edge case da spec: "Schema Registry indisponível" reportado de forma distinta).

## TASK-045 [X]
Implementar `app/registry/client.py`: cliente HTTP do Schema Registry com
método de teste de conectividade, respeitando o timeout de 10 segundos
(decisão Q2) e sem efeitos colaterais (NFR-002).

Story: US-005a

Definition of Done:
- Um Schema Registry acessível retorna sucesso ao testar (cenário 1 do Acceptance Scenario de US-005a).
- Um Schema Registry inacessível ou mal configurado retorna falha com motivo compreensível (cenário 2).
- Nenhum schema é registrado ou alterado durante o teste.

## TASK-046 [X]
Estender `app/api/routes/configurations.py` para incluir o teste de
Schema Registry na rota `POST /api/v1/configurations/{name}/test` quando o
bloco `schema_registry` estiver presente.

Story: US-005a

Definition of Done:
- A rota de teste retorna o resultado de Kafka e de Schema Registry de forma separada e identificável.
- Quando não há `schema_registry` configurado, a rota não tenta testá-lo e não reporta falha por isso.

## TASK-047 [X]
Implementar `app/ui/pages/configuracoes_schema_registry.py`: formulário de
URL/credenciais/certificados e botão "Testar Schema Registry".

Story: US-005a

Definition of Done:
- Um desenvolvedor consegue configurar e testar o Schema Registry de forma independente da configuração Kafka (Caso de Uso de US-005a).
- O resultado do teste (sucesso ou falha com motivo) é exibido claramente na tela.

## TASK-048 [X]
Estender `app/registry/client.py` (TASK-045) com métodos para listar
subjects/versões existentes e para registrar/checar a existência de um
schema idêntico antes de criar uma nova versão (usando o endpoint nativo
de compatibilidade do Schema Registry, conforme mitigação de risco da
seção 11 do plano).

Story: US-005b

Definition of Done:
- A listagem de subjects retorna os subjects e versões reais do Schema Registry configurado (cenário 1 do Acceptance Scenario de US-005b).
- Reenviar um schema idêntico para o mesmo subject reaproveita o schema já registrado, sem criar uma nova versão desnecessária (cenário 2, FR-015, SC-008, edge case da spec).

## TASK-049 [X]
Estender `app/kafka/serializer.py` (TASK-032) para usar o schema id
retornado pelo Schema Registry (via TASK-048) na serialização, quando o
Schema Registry estiver configurado.

Story: US-005b

Definition of Done:
- A serialização usa o schema id do Schema Registry quando disponível, sem quebrar o caminho de serialização apenas com `.avsc` local (FR-015).

## TASK-050 [X]
Estender `app/ui/pages/schemas_avro.py` (TASK-023/TASK-025) com um seletor
de subject/versão do Schema Registry como alternativa ao upload de um novo
arquivo `.avsc`.

Story: US-005b

Definition of Done:
- Um desenvolvedor consegue selecionar um schema existente no Schema Registry em vez de fazer upload de um arquivo (cenário 1 do Acceptance Scenario de US-005b, FR-019).
- O schema selecionado dessa forma é utilizável nos mesmos fluxos de validação e publicação que um `.avsc` local.

## TASK-051 [X]
Estender `app/config/manager.py` (TASK-008) reforçando a validação de
unicidade de nome e o isolamento entre registros ao editar uma
configuração entre três ou mais ambientes cadastrados.

Story: US-006

Definition of Done:
- Criar três configurações com nomes distintos deixa todas disponíveis para seleção (cenário 1 do Acceptance Scenario de US-006, SC-006).
- Editar uma configuração não altera as demais (cenário 2).
- Duas tentativas de configuração com o mesmo nome são impedidas ou claramente diferenciadas (cenário 4, edge case da spec).

## TASK-052 [X]
Implementar em `app/ui/components/` um seletor de ambiente (Configuração de
Ambiente) reutilizável, usado tanto na tela Publicar Mensagem quanto na
tela de Testar Conexão.

Story: US-006

Definition of Done:
- Selecionar uma configuração específica ao publicar usa exatamente os dados de Kafka e Schema Registry daquela configuração (cenário 3 do Acceptance Scenario de US-006).
- O mesmo componente de seleção é reutilizado nas duas telas, sem duplicar lógica de listagem de configurações.

---

### Fase 5: User Stories P3 — observabilidade local

## TASK-053 [X]
Implementar em `services/kafka_service.py` um método de estado agregado
que resume: última conexão Kafka testada, status do Schema Registry,
configuração ativa, contagem de schemas carregados e dados da última
mensagem publicada.

Story: US-007a

Definition of Done:
- O método retorna todos os dados exigidos por FR-023 a partir do log de operações (TASK-010) e do armazenamento local de schemas/configurações.
- O cálculo não exige nenhum banco de dados ou índice adicional.

## TASK-054 [X]
Implementar `app/ui/pages/dashboard.py`: página inicial exibindo status de
conexão do Kafka e do Schema Registry, configuração ativa, quantidade de
schemas carregados e dados da última mensagem publicada.

Story: US-007a

Definition of Done:
- Ao abrir a tela inicial após uma configuração ativa testada com sucesso, todos os dados exigidos por FR-023 aparecem corretamente (cenário único do Acceptance Scenario de US-007a).
- Os dados exibidos refletem operações reais realizadas anteriormente (teste de conexão, publicação), não valores estáticos ou de exemplo.

## TASK-055 [X]
Garantir em `services/kafka_service.py` que cada operação relevante (teste
de conexão, teste de Schema Registry, validação de schema, validação de
payload, publicação) é registrada no log diário (TASK-010) com todos os
campos mínimos de FR-024.

Story: US-007b

Definition of Done:
- Toda chamada aos métodos `test_connection`, `test_schema_registry`, `validate_schema`, `validate_payload` e `publish` gera exatamente um Registro de Operação.
- Uma operação que falhou tem seu detalhe técnico de erro preservado e recuperável a partir do log (cenário 2 do Acceptance Scenario de US-007b).

## TASK-056 [X]
Implementar `app/ui/pages/logs.py`: tabela do histórico de operações com
filtro por resultado e por tipo de operação.

Story: US-007b

Definition of Done:
- A tela exibe data/hora, tipo de operação, tópico, schema, resultado e duração de operações recentes (cenário 1 do Acceptance Scenario de US-007b, FR-025).
- Consultar uma operação que falhou permite encontrar a mensagem de erro técnica associada, suficiente para investigar a causa sem examinar código-fonte (cenário 2, SC-007).

## TASK-057 [X]
Implementar (opcional) uma rota `GET /api/v1/logs` em `app/api/routes/`
expondo o histórico de operações para consumo por automação.

Story: US-007b

Definition of Done:
- A rota retorna o mesmo conjunto de dados exibido na tela de Logs (TASK-056), preservando NFR-006.
- Ausência desta rota não bloqueia nenhuma outra story — é estritamente aditiva.

---

### Fase 6: Polimento e Cross-Cutting

## TASK-058 [X]
Escrever testes unitários para `avro/schema_loader.py` e
`avro/validator.py`: schemas válidos/inválidos, tipos simples e compostos,
payload válido, tipo incompatível, union opcional nula, campos extras/
ausentes.

Story: N/A (cross-cutting; cobre US-002a, US-002b, US-003a)

Definition of Done:
- Todos os cenários listados na seção 12 do plano para estes dois módulos têm um teste unitário correspondente.
- Os testes rodam sem depender de um broker Kafka ou Schema Registry real.

## TASK-059 [X]
Escrever testes unitários para `config/manager.py`: unicidade de nome,
isolamento entre configurações.

Story: N/A (cross-cutting; cobre US-006)

Definition of Done:
- Um teste cobre a tentativa de criar duas configurações com o mesmo nome.
- Um teste cobre a edição de uma configuração e confirma que as demais permanecem inalteradas.

## TASK-060
Escrever testes de integração (Kafka e Schema Registry locais via
`docker-compose`, quando disponíveis) para `kafka/connection.py` (SSL,
SASL/PLAIN), `kafka/producer.py` + `kafka/serializer.py` (publicação de
ponta a ponta) e `registry/client.py` (conectividade, listagem de
subjects, reaproveitamento de schema idêntico).

Story: N/A (cross-cutting; cobre US-001b, US-003b, US-005a, US-005b)

Definition of Done:
- Os testes de integração sobem Kafka/Schema Registry via `docker-compose` (profile opcional da TASK-003).
- Uma publicação de ponta a ponta é confirmada com partição e offset reais retornados pelo broker de teste.
- Reenviar um schema idêntico não cria uma nova versão no Schema Registry de teste.

## TASK-061 [X]
Escrever testes de API usando `TestClient` do FastAPI para cada rota de
`api/routes/`, incluindo casos de erro (configuração/schema inexistentes)
e verificando paridade de resultado com o fluxo de UI (NFR-006).

Story: N/A (cross-cutting; cobre US-004a e NFR-006)

Definition of Done:
- Cada rota tem ao menos um teste de caminho feliz e um teste de caso de erro.
- Um teste compara explicitamente o resultado de `POST /api/v1/messages` com o resultado equivalente produzido via `services/kafka_service.py` chamado a partir da simulação da UI.

## TASK-062
Escrever/atualizar `README.md` com pré-requisitos de instalação por sistema
operacional para `confluent-kafka`/`librdkafka` (risco da seção 11 do
plano) e instruções de instalação/execução local, reforçando NFR-005.

Story: N/A (cross-cutting; mitigação de risco da seção 11)

Definition of Done:
- O README lista pré-requisitos específicos para Linux, macOS e Windows (ou WSL) para instalar `confluent-kafka`.
- Um desenvolvedor consegue instalar e executar a ferramenta localmente seguindo apenas o README, sem depender de conhecimento prévio do código.

## TASK-063
Documentar e executar manualmente o roteiro de validação de ponta a ponta
descrito na seção 14 do plano (cadastrar configuração, testar conexão,
carregar schema, validar e publicar payload pela tela e via `curl`,
conferir Dashboard e Logs).

Story: N/A (cross-cutting; validação final de todas as stories P1/P3)

Definition of Done:
- Cada um dos 6 passos do roteiro da seção 14 do plano foi executado manualmente com um Kafka acessível (real ou local via TASK-003) e o resultado documentado.
- O resultado obtido via `curl` no passo 5 é idêntico ao obtido pela tela para a mesma configuração, schema e payload (SC-005).

## TASK-064 [X]
Revisar a base de código garantindo que `ui/` e `api/` nunca chamam
`kafka/`, `avro/` ou `registry/` diretamente, apenas via
`services/kafka_service.py` (mitigação de risco da seção 11 do plano,
garantia de NFR-006).

Story: N/A (cross-cutting; revisão arquitetural final)

Definition of Done:
- Uma checagem estática (grep ou lint de imports) confirma ausência de imports diretos de `kafka/`, `avro/` ou `registry/` a partir de `ui/` ou `api/`.
- Qualquer violação encontrada foi corrigida antes do fechamento desta tarefa.

---

## Exemplo de Execução Paralela (por story)

Dentro de uma mesma fase de story, tarefas que tocam arquivos diferentes e
não dependem de uma tarefa anterior incompleta podem ser executadas em
paralelo. Exemplos:

- US-001a: TASK-012 (`api/schemas/configurations.py`) pode ser feita em
  paralelo com o início de TASK-014 (`ui/pages/configuracoes_kafka.py`),
  desde que ambas dependam apenas de TASK-007/TASK-008 já concluídas.
- US-002a/US-002b: TASK-021 (tipos simples) e TASK-024 (tipos compostos)
  tocam o mesmo arquivo (`avro/schema_loader.py`) e por isso **não** devem
  rodar em paralelo entre si, mas TASK-022 (`api/routes/schema.py`) pode
  avançar em paralelo com TASK-024 depois que TASK-021 estiver concluída.
- Fase 6 (Polimento): TASK-058, TASK-059, TASK-060 e TASK-061 tocam
  suítes de teste independentes e podem ser executadas em paralelo entre
  si, desde que as fases correspondentes (2 a 5) já estejam concluídas.

## Estratégia de Implementação

1. Concluir Fase 1 (Setup) e Fase 2 (Fundação) — nada nas fases seguintes é
   testável sem elas.
2. Concluir Fase 3 (US-001a até US-004b) como **MVP**: entrega o fluxo
   completo de configurar, carregar schema, validar, publicar — pela tela e
   pela API — que é o resultado central do briefing aprovado.
3. Concluir Fase 4 (US-005a, US-005b, US-006) para suportar Schema Registry
   e múltiplos ambientes corporativos.
4. Concluir Fase 5 (US-007a, US-007b) para fechar o ciclo de
   troubleshooting sem exigir leitura de código-fonte.
5. Concluir Fase 6 (Polimento) como fechamento de qualidade antes de
   considerar a feature 001 pronta para uso corporativo real.
