---
stage: spec
status: approved
sourceSkill:
  id: speckit-specify
  version: 469fb87de970269440368e5cce234768a346bb0a74fb75166e3664405cdf43b9
approvedBy: bruno
approvedAt: '2026-08-23T00:37:49.682Z'
---

# Feature Specification: KafkaForge — Envio de Mensagens Avro para o Kafka Corporativo

**Feature**: 001
**Diretório**: `.squad/features/001`
**Criado em**: 2026-08-22
**Status**: Draft
**Entrada**: `.squad/features/001/briefing.md`

## Resumo

Criar o **KafkaForge**, uma ferramenta local de apoio ao desenvolvimento que permite
configurar uma conexão com o Kafka corporativo (e, opcionalmente, com um Schema
Registry), carregar e validar schemas Avro, montar e validar payloads, e publicar
mensagens em tópicos Kafka — tanto por uma interface manual quanto por um serviço
local que outras automações possam chamar. O objetivo é eliminar a necessidade de
scripts avulsos para testar publicações Avro durante o desenvolvimento.

## User Scenarios & Testing (mandatory)

### User Story 1 - Configurar e testar a conexão com o Kafka (Priority: P1)

Um desenvolvedor abre o KafkaForge pela primeira vez, informa os dados de conexão
do Kafka corporativo (endereço dos brokers, protocolo de segurança, credenciais
e/ou certificados) e confirma que a conexão está funcionando antes de tentar
publicar qualquer mensagem.

**Why this priority**: sem uma conexão configurada e validada, nenhuma outra
funcionalidade da ferramenta (carregar schema, montar payload, publicar) pode ser
utilizada de forma confiável. É o pré-requisito de tudo.

**Independent Test**: pode ser testado isoladamente preenchendo os dados de uma
conexão Kafka (real ou de teste) e acionando "Testar conexão", verificando que o
resultado (sucesso ou falha com motivo) reflete o estado real do broker informado.

**Acceptance Scenarios**:

1. **Given** um desenvolvedor sem nenhuma configuração salva, **When** ele
   preenche nome da configuração, endereço dos brokers, protocolo de segurança e
   credenciais/certificados aplicáveis, **Then** a configuração é salva localmente
   e pode ser reaberta posteriormente.
2. **Given** uma configuração de Kafka válida e um broker acessível, **When** o
   desenvolvedor aciona "Testar conexão", **Then** a ferramenta indica
   claramente que a conexão foi estabelecida, sem publicar nenhuma mensagem.
3. **Given** uma configuração de Kafka com um dado incorreto (broker
   inexistente, credencial inválida ou certificado incorreto), **When** o
   desenvolvedor aciona "Testar conexão", **Then** a ferramenta indica
   claramente que a conexão falhou e apresenta uma mensagem compreensível sobre
   o motivo.

---

### User Story 2 - Carregar e validar um schema Avro (Priority: P1)

Um desenvolvedor faz upload de um arquivo `.avsc` e a ferramenta confirma se o
schema é válido, mostrando nome, namespace, campos e tipos, para que ele possa
confirmar que carregou o schema correto antes de montar uma mensagem.

**Why this priority**: toda validação e serialização de payload depende de um
schema Avro corretamente carregado; é a segunda peça fundamental do fluxo,
independente da conexão Kafka já estar configurada.

**Independent Test**: pode ser testado isoladamente enviando um arquivo `.avsc`
válido e um inválido, e verificando que a ferramenta reage de forma diferente e
compreensível em cada caso, sem depender de nenhuma configuração de Kafka.

**Acceptance Scenarios**:

1. **Given** um arquivo `.avsc` válido, **When** o desenvolvedor faz upload
   dele na tela de Schemas Avro, **Then** a ferramenta exibe nome, namespace,
   lista de campos com seus tipos e o conteúdo original do schema.
2. **Given** um arquivo `.avsc` com uma estrutura inválida, **When** o
   desenvolvedor tenta fazer o upload, **Then** a ferramenta rejeita o schema e
   explica de forma compreensível qual é o problema.
3. **Given** um schema contendo tipos complexos (union, enum, array, map,
   record, incluindo um campo opcional do tipo `["null", "string"]`), **When**
   o schema é carregado, **Then** todos os campos e seus tipos (incluindo os
   tipos compostos) são exibidos corretamente.

---

### User Story 3 - Montar, validar e publicar uma mensagem pela interface (Priority: P1)

Com uma configuração de Kafka testada e um schema carregado, o desenvolvedor
monta um payload (via editor JSON), valida esse payload contra o schema e
publica a mensagem no tópico desejado, conferindo a partição e o offset
retornados.

**Why this priority**: é o fluxo-fim-a-fim que resolve o problema original do
briefing — publicar uma mensagem Avro válida no Kafka corporativo a partir de
uma interface, sem scripts avulsos.

**Independent Test**: pode ser testado isoladamente com uma configuração Kafka
e um schema já preparados: preencher um payload válido, validar, publicar e
conferir que a resposta mostra tópico, partição e offset; repetir com um
payload inválido e conferir que a publicação é bloqueada antes de chegar ao
Kafka.

**Acceptance Scenarios**:

1. **Given** uma configuração Kafka testada e um schema carregado, **When** o
   desenvolvedor informa um payload compatível com o schema e aciona
   "Validar", **Then** a ferramenta confirma que o payload é válido.
2. **Given** um payload com um campo de tipo incompatível com o schema (por
   exemplo, texto em um campo numérico), **When** o desenvolvedor aciona
   "Validar" ou "Publicar", **Then** a ferramenta informa qual campo está
   incorreto, o tipo esperado e o tipo recebido, e não publica a mensagem.
3. **Given** um payload válido, uma configuração Kafka testada, um schema
   carregado e um tópico informado, **When** o desenvolvedor aciona
   "Publicar", **Then** a mensagem é enviada ao Kafka e a ferramenta exibe
   tópico, partição e offset da mensagem publicada.
4. **Given** uma falha durante a publicação (por exemplo, tópico inexistente
   ou perda de conexão), **When** o desenvolvedor aciona "Publicar", **Then**
   a ferramenta informa claramente que a publicação falhou e apresenta a
   mensagem de erro correspondente.

---

### User Story 4 - Publicar uma mensagem via automação (serviço local) (Priority: P1)

Um script ou sistema externo, sem abrir a interface gráfica, envia uma
requisição para o serviço local do KafkaForge informando configuração, tópico,
schema e payload, e recebe de volta a confirmação da publicação (ou o motivo do
erro).

**Why this priority**: é o segundo resultado esperado explícito do briefing —
disponibilizar a mesma capacidade de publicação para automações, não apenas
para uso manual pela tela. Sem isso, a ferramenta não cobre o caso de uso de
integração com scripts.

**Independent Test**: pode ser testado isoladamente chamando o serviço local a
partir de uma automação (por exemplo, uma chamada HTTP de linha de comando),
sem interagir com a interface gráfica, e verificando que o resultado (sucesso
com partição/offset, ou erro descritivo) é equivalente ao obtido publicando a
mesma mensagem pela tela.

**Acceptance Scenarios**:

1. **Given** uma configuração e um schema já cadastrados no KafkaForge, **When**
   uma automação externa envia um pedido de publicação informando
   configuração, tópico, schema e payload, **Then** o serviço valida o
   payload, publica a mensagem e retorna tópico, partição e offset.
2. **Given** um payload incompatível com o schema informado, **When** a
   automação envia o pedido de publicação, **Then** o serviço recusa a
   publicação e retorna uma indicação de erro compreensível, sem tentar
   publicar no Kafka.
3. **Given** uma configuração ou um schema inexistentes informados pela
   automação, **When** o pedido é enviado, **Then** o serviço retorna um erro
   indicando que a configuração ou o schema não foram encontrados.
4. **Given** o serviço local em execução, **When** um desenvolvedor consulta a
   documentação interativa do serviço, **Then** ele encontra a lista de
   operações disponíveis e consegue testar cada uma diretamente por ali.

---

### User Story 5 - Configurar e testar o Schema Registry (Priority: P2)

Um desenvolvedor configura, de forma independente da conexão Kafka, o acesso a
um Schema Registry corporativo, testa se ele está acessível e passa a poder
consultar e reutilizar schemas já registrados em vez de sempre subir um novo
arquivo `.avsc`.

**Why this priority**: melhora o fluxo ao evitar duplicidade de schemas e ao
aproximar o comportamento da ferramenta do ambiente corporativo real, mas o
fluxo básico de publicação (US3/US4) já funciona sem Schema Registry, serializando
diretamente a partir do `.avsc`.

**Independent Test**: pode ser testado isoladamente configurando um Schema
Registry e acionando "Testar Schema Registry" sem que nenhuma configuração de
Kafka precise existir; e, em seguida, consultando subjects/versões já
existentes nesse registry.

**Acceptance Scenarios**:

1. **Given** um Schema Registry acessível, **When** o desenvolvedor informa a
   URL (e credenciais/certificados, se necessário) e aciona "Testar Schema
   Registry", **Then** a ferramenta confirma que o Schema Registry está
   acessível.
2. **Given** um Schema Registry inacessível ou mal configurado, **When** o
   desenvolvedor aciona "Testar Schema Registry", **Then** a ferramenta
   informa claramente que a verificação falhou e por quê.
3. **Given** um Schema Registry configurado e acessível, **When** o
   desenvolvedor consulta os subjects disponíveis, **Then** ele visualiza a
   lista de subjects e consegue selecionar um schema existente em vez de
   fazer upload de um novo arquivo.
4. **Given** um schema que já existe registrado no Schema Registry, **When** o
   desenvolvedor tenta publicar novamente um schema idêntico, **Then** a
   ferramenta reaproveita o schema já registrado em vez de criar um registro
   duplicado.
5. **Given** nenhum Schema Registry configurado para o ambiente selecionado,
   **When** o desenvolvedor publica uma mensagem, **Then** a ferramenta
   serializa a mensagem diretamente a partir do `.avsc` carregado, sem exigir
   Schema Registry.

---

### User Story 6 - Gerenciar múltiplas configurações de ambiente (Priority: P2)

Um desenvolvedor cadastra e mantém mais de uma configuração (por exemplo,
Desenvolvimento, Homologação e Produção), cada uma com seus próprios dados de
Kafka e de Schema Registry, e alterna entre elas ao publicar mensagens.

**Why this priority**: é essencial para o uso real no dia a dia (testar contra
mais de um ambiente), mas depende das capacidades já cobertas pelas User
Stories 1 e 5; sem elas, não haveria o que gerenciar.

**Independent Test**: pode ser testado isoladamente criando três configurações
com nomes diferentes, editando uma delas, e confirmando que as outras duas
permanecem intactas.

**Acceptance Scenarios**:

1. **Given** nenhuma configuração cadastrada, **When** o desenvolvedor cria
   três configurações com nomes distintos, **Then** todas ficam disponíveis
   para seleção nas telas de publicação e de teste de conexão.
2. **Given** múltiplas configurações cadastradas, **When** o desenvolvedor
   edita os dados de uma delas, **Then** as demais configurações permanecem
   inalteradas.
3. **Given** múltiplas configurações cadastradas, **When** o desenvolvedor
   seleciona uma configuração específica para publicar uma mensagem, **Then**
   a publicação usa exatamente os dados de Kafka e de Schema Registry daquela
   configuração.

---

### User Story 7 - Acompanhar status e histórico de operações (Priority: P3)

Um desenvolvedor abre a tela inicial e vê rapidamente se o Kafka e o Schema
Registry estão acessíveis, qual configuração está ativa, quantos schemas estão
carregados e qual foi a última mensagem publicada; e, quando algo falha, ele
consulta o histórico de operações para investigar o que aconteceu.

**Why this priority**: é um recurso de conveniência e de troubleshooting que
melhora a experiência, mas não bloqueia o fluxo central de configurar,
validar e publicar mensagens já coberto pelas demais histórias.

**Independent Test**: pode ser testado isoladamente realizando algumas
operações (teste de conexão, validação, publicação) e depois abrindo a tela
inicial e a tela de histórico para conferir se os dados exibidos refletem as
operações realizadas.

**Acceptance Scenarios**:

1. **Given** uma configuração ativa testada com sucesso, **When** o
   desenvolvedor abre a tela inicial, **Then** ele vê o status de conexão do
   Kafka e do Schema Registry, a configuração ativa, a quantidade de schemas
   carregados e os dados da última mensagem publicada.
2. **Given** operações realizadas anteriormente (testes, validações,
   publicações com sucesso ou falha), **When** o desenvolvedor abre a tela de
   histórico, **Then** ele visualiza as operações recentes com data/hora,
   tipo de operação, tópico, schema, resultado e duração.
3. **Given** uma operação que falhou, **When** o desenvolvedor consulta o
   registro dessa operação no histórico, **Then** ele encontra a mensagem de
   erro técnica associada, suficiente para investigar a causa.

---

### Edge Cases

- Payload contendo um campo do tipo união opcional (`["null", "string"]` ou
  equivalente) recebendo o valor ausente/nulo: a validação deve aceitar
  corretamente tanto a ausência do valor quanto o tipo alternativo definido na
  união.
- Arquivo `.avsc` sintaticamente válido como JSON, mas semanticamente inválido
  como schema Avro (por exemplo, tipo desconhecido ou estrutura de `record`
  incompleta): deve ser rejeitado com uma explicação, e não apenas travar ou
  ser aceito silenciosamente.
- Payload contendo campos extras não previstos no schema, ou omitindo campos
  obrigatórios: ambos os casos devem ser sinalizados como inválidos antes de
  qualquer tentativa de publicação.
- Conexão Kafka perdida no meio de uma publicação: a ferramenta deve informar
  a falha e não deve apresentar a publicação como bem-sucedida sem confirmação
  do broker.
- Tópico informado não existe no cluster: a tentativa de publicação deve
  falhar de forma clara, indicando o problema.
- Schema Registry configurado, mas indisponível no momento da publicação: a
  ferramenta deve informar a falha relacionada ao Schema Registry de forma
  distinta de uma falha de conexão com o Kafka.
- Tentativa de registrar no Schema Registry um schema já existente e idêntico
  para o mesmo subject: a ferramenta deve reconhecer o schema existente e não
  criar uma nova versão desnecessária.
- Duas configurações de ambiente com o mesmo nome: a ferramenta deve impedir a
  duplicidade de nomes ou deixar claro qual configuração está sendo usada.
- Certificado de cliente informado sem a senha da chave privada (quando a
  chave exige senha): o teste de conexão deve falhar com uma mensagem que
  aponte esse problema especificamente.
- Uso simultâneo da interface gráfica e do serviço de automação sobre a mesma
  configuração: ambos devem operar sobre os mesmos dados de configuração e
  produzir resultados de publicação consistentes entre si.

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: A ferramenta MUST permitir criar, salvar, editar e remover
  configurações de conexão com o Kafka, cada uma identificada por um nome
  (por exemplo, "Desenvolvimento", "Homologação", "Produção").
- **FR-002**: Cada configuração de Kafka MUST suportar, no mínimo: endereço
  dos brokers, protocolo de segurança (incluindo variantes sem
  autenticação, apenas com criptografia de transporte, e com autenticação por
  usuário/senha), mecanismo de autenticação por usuário/senha, e autenticação
  por certificado (certificado de autoridade, certificado de cliente, chave
  privada de cliente e, quando aplicável, senha da chave privada).
- **FR-003**: A ferramenta MUST permitir anexar certificados por meio de
  upload de arquivo.
- **FR-004**: A ferramenta MUST oferecer uma ação de "testar conexão" que
  verifica se é possível conectar ao Kafka usando a configuração informada,
  sem publicar nenhuma mensagem, e MUST reportar claramente sucesso ou falha
  (com o motivo, em caso de falha).
- **FR-005**: A ferramenta MUST permitir configurar o acesso a um Schema
  Registry (URL, usuário/senha e certificados quando aplicável) de forma
  independente da configuração do Kafka.
- **FR-006**: A ferramenta MUST oferecer uma ação de "testar Schema Registry"
  que verifica se o Schema Registry configurado está acessível, reportando
  claramente sucesso ou falha.
- **FR-007**: A configuração do Schema Registry MUST ser opcional; quando
  ausente para um determinado ambiente, a ferramenta MUST continuar
  permitindo validar e publicar mensagens usando apenas o schema `.avsc`
  carregado localmente.
- **FR-008**: A ferramenta MUST permitir o upload de arquivos de schema Avro
  (`.avsc`), validando sua estrutura e exibindo nome, namespace, lista de
  campos com seus respectivos tipos, e o conteúdo original do schema.
- **FR-009**: Quando um arquivo de schema for inválido, a ferramenta MUST
  informar de forma compreensível qual é o problema, sem interromper o uso
  das demais funcionalidades.
- **FR-010**: A ferramenta MUST suportar corretamente os tipos de dado Avro:
  string, int, long, float, double, boolean, bytes, null, enum, array, map,
  record e union — incluindo campos opcionais representados como união com
  `null` (ex.: `["null", "string"]`).
- **FR-011**: Após selecionar um schema, a ferramenta MUST permitir montar ou
  editar um payload por meio de um editor de texto no formato JSON.
- **FR-012**: A ferramenta SHOULD, como melhoria sobre o editor JSON, gerar
  automaticamente um formulário com um campo por atributo do schema
  selecionado, mantendo o editor JSON disponível como alternativa.
- **FR-013**: A ferramenta MUST validar o payload informado contra o schema
  Avro selecionado antes de qualquer tentativa de publicação, indicando
  claramente se o payload é válido e, quando inválido, apontando o campo
  problemático, o tipo esperado e o tipo recebido.
- **FR-014**: Quando o payload for válido, a ferramenta MUST serializar o
  payload no formato Avro binário compatível com o schema selecionado.
- **FR-015**: Quando o Schema Registry estiver configurado, a ferramenta MUST
  utilizá-lo no fluxo de publicação (consulta/registro de schema conforme
  necessário), evitando registrar novamente um schema já existente e
  idêntico.
- **FR-016**: A ferramenta MUST permitir publicar a mensagem serializada em um
  tópico Kafka informado, usando a configuração de ambiente selecionada.
- **FR-017**: Após uma publicação bem-sucedida, a ferramenta MUST exibir o
  tópico, a partição e o offset retornados pelo Kafka.
- **FR-018**: Após uma falha de publicação, a ferramenta MUST exibir uma
  indicação clara de falha acompanhada da mensagem de erro correspondente.
- **FR-019**: Quando o Schema Registry estiver configurado e acessível, a
  ferramenta MUST permitir consultar os subjects e versões existentes e
  selecionar um schema já registrado como alternativa ao upload de um novo
  arquivo `.avsc`.
- **FR-020**: A ferramenta MUST disponibilizar um serviço local (acessível via
  requisição HTTP) que permita, sem uso da interface gráfica: consultar o
  estado do serviço; listar e cadastrar configurações; testar uma
  configuração; validar um schema; validar um payload contra um schema; e
  publicar uma mensagem.
- **FR-021**: A operação de publicação via serviço local MUST executar o mesmo
  fluxo de validação, serialização e publicação usado pela interface gráfica,
  retornando tópico, partição e offset em caso de sucesso, ou uma indicação de
  erro compreensível em caso de falha (incluindo os casos de configuração ou
  schema não encontrados).
- **FR-022**: A ferramenta MUST disponibilizar documentação interativa das
  operações oferecidas pelo serviço local, permitindo consultar e testar cada
  operação diretamente por essa documentação.
- **FR-023**: A ferramenta MUST exibir uma tela inicial com o status atual da
  conexão com o Kafka, o status do Schema Registry, a configuração ativa, a
  quantidade de schemas carregados e os dados da última mensagem publicada.
- **FR-024**: A ferramenta MUST registrar um histórico de operações (testes de
  conexão, validações e publicações) contendo, no mínimo: data/hora, tipo de
  operação, tópico, schema, partição, offset, resultado (sucesso/erro),
  duração e detalhe técnico do erro quando aplicável.
- **FR-025**: A ferramenta MUST oferecer uma tela para consultar o histórico
  de operações recentes.
- **FR-026**: Para as categorias de falha mais comuns (conexão, autenticação,
  autorização, schema, validação de payload, serialização e publicação), a
  ferramenta MUST apresentar uma mensagem compreensível para o desenvolvedor,
  mantendo o detalhe técnico disponível para consulta (por exemplo, no
  histórico de operações).

### Non-Functional Requirements

- **NFR-001**: A ferramenta MUST ser executada inteiramente no ambiente local
  do desenvolvedor; nenhum dado de configuração, credencial, schema ou
  payload MUST ser enviado a qualquer serviço externo além do Kafka e do
  Schema Registry corporativos explicitamente configurados pelo
  desenvolvedor.
- **NFR-002**: As ações de "testar conexão" e "testar Schema Registry" MUST
  ser livres de efeitos colaterais sobre os dados do cluster — ou seja, não
  MUST publicar mensagens nem registrar/alterar schemas.
- **NFR-003**: Credenciais e certificados informados pelo desenvolvedor MUST
  ser armazenados apenas na configuração local da ferramenta, sem exigir
  integração com um sistema corporativo de gerenciamento de segredos.
- **NFR-004**: As ações de teste de conexão e de publicação MUST apresentar um
  resultado (sucesso, falha ou expiração por tempo) em um intervalo curto e
  previsível, evitando que a interface ou o serviço local fiquem
  indefinidamente sem resposta.
- **NFR-005**: A ferramenta MUST permanecer simples de instalar, configurar e
  executar por um único desenvolvedor, sem exigir um banco de dados ou outra
  infraestrutura além do Kafka e do Schema Registry alvo.
- **NFR-006**: Toda operação disponível pela interface gráfica (testar
  conexão, testar Schema Registry, validar schema, validar payload, publicar
  mensagem) MUST também estar disponível pelo serviço local de automação, com
  comportamento equivalente.

## Key Entities

- **Configuração de Ambiente**: representa um conjunto nomeado de dados de
  acesso (ex.: "Desenvolvimento", "Homologação", "Produção"). Contém os dados
  de conexão com o Kafka (brokers, protocolo de segurança, mecanismo de
  autenticação, credenciais, certificados) e, de forma independente e
  opcional, os dados de acesso ao Schema Registry (URL, credenciais,
  certificados). É a unidade selecionada ao testar conexões e ao publicar
  mensagens.
- **Schema Avro**: representa um schema carregado via arquivo `.avsc` ou
  obtido de um Schema Registry configurado. Possui nome, namespace, lista de
  campos com seus tipos (incluindo tipos compostos como union, array, map,
  enum e record), conteúdo original e um estado de validade.
- **Payload**: conteúdo (inicialmente em formato JSON) que um desenvolvedor
  associa a um Schema Avro para validação e posterior publicação. Possui um
  estado de validação e, quando inválido, uma lista de problemas encontrados
  por campo.
- **Registro de Operação**: representa uma ação realizada pela ferramenta
  (teste de conexão, teste de Schema Registry, validação de schema, validação
  de payload ou publicação de mensagem), com data/hora, tipo, contexto
  (configuração, tópico, schema quando aplicável), resultado, duração e
  detalhe técnico em caso de erro. É a base tanto da tela de histórico quanto
  dos indicadores exibidos na tela inicial.

## Success Criteria (mandatory)

### Measurable Outcomes

- **SC-001**: Um desenvolvedor consegue, na primeira utilização, ir da
  abertura da ferramenta até a publicação de uma primeira mensagem de teste
  válida no Kafka corporativo, usando apenas as próprias telas da ferramenta.
- **SC-002**: 100% dos testes de conexão realizados refletem corretamente se o
  Kafka informado está de fato acessível, apresentando um motivo compreensível
  sempre que a conexão falha.
- **SC-003**: 100% dos payloads que não correspondem ao schema Avro associado
  são bloqueados antes de qualquer tentativa de publicação no Kafka, com
  indicação do campo e do tipo esperado versus recebido.
- **SC-004**: Após uma publicação bem-sucedida, o desenvolvedor encontra
  tópico, partição e offset diretamente na mesma tela ou resposta, sem
  precisar consultar nenhuma outra ferramenta.
- **SC-005**: Uma automação externa consegue publicar uma mensagem chamando
  apenas o serviço local da ferramenta (sem abrir a interface gráfica) e
  obter um resultado equivalente ao de uma publicação manual feita pela tela,
  para a mesma configuração, schema e payload.
- **SC-006**: Um desenvolvedor consegue manter pelo menos três configurações
  de ambiente distintas simultaneamente, sem que a edição de uma delas afete
  as demais.
- **SC-007**: Diante de qualquer falha (conexão, validação ou publicação), o
  desenvolvedor consegue identificar a causa raiz a partir das mensagens
  exibidas e/ou do histórico de operações, sem precisar examinar o código-fonte
  da ferramenta.
- **SC-008**: Um schema já registrado no Schema Registry não é duplicado ao
  ser reenviado de forma idêntica pela ferramenta.

## Assumptions

- Uso local por um único desenvolvedor por instância da ferramenta; não é
  necessário controle de acesso multiusuário nem permissões diferenciadas.
- Não há necessidade de um banco de dados; configurações e histórico de
  operações podem ser mantidos em armazenamento local simples.
- Não é necessário um sistema corporativo de gerenciamento de segredos; o
  desenvolvedor é responsável pelas credenciais e certificados armazenados
  localmente na sua própria máquina.
- Não é necessária autenticação de usuários para acessar a interface ou o
  serviço local nesta etapa, pois o uso é local e individual.
- O ambiente de rede do desenvolvedor (VPN ou equivalente) já permite alcançar
  o Kafka e o Schema Registry corporativos; a ferramenta não precisa resolver
  problemas de conectividade de rede além de reportá-los.
- O Schema Registry é opcional por configuração de ambiente; quando ausente,
  os recursos que dependem dele (consulta de subjects/versões, reuso de
  schema remoto) simplesmente não ficam disponíveis para aquele ambiente,
  sem impedir a publicação via `.avsc` local.
- A geração automática de formulário a partir do schema é uma melhoria
  desejável, mas o editor JSON é o mecanismo mínimo obrigatório para compor
  um payload.

## Out of Scope

- Autenticação de usuários, OAuth ou controle de acesso baseado em papéis
  (RBAC) para a própria ferramenta.
- Integração com sistemas corporativos de gerenciamento de segredos (ex.:
  Vault) ou qualquer gestão avançada de segredos.
- Implantação em Kubernetes ou integração com plataformas corporativas de
  observabilidade/auditoria.
- Suporte a múltiplos usuários simultâneos ou a múltiplos "tenants" na mesma
  instância da ferramenta.
- Persistência dos dados em banco de dados.
- Disponibilização pública da ferramenta ou de seu serviço local fora da
  máquina do desenvolvedor.
- Negociação avançada de evolução/compatibilidade de schemas além de evitar o
  registro duplicado de um schema idêntico já existente.
