---
stage: split
status: approved
sourceSkill:
  id: user-story-splitting
  version: dbee8a37e4f437479d2bcc103e14e4badd758c09be45268f4d7af46d204207a7
applied: true
---

# Relatório de Revisão de Tamanho das User Stories — Feature 001

## Resumo executivo

Das 7 user stories revisadas, **6 são grandes demais para serem implementadas, testadas e revisadas de forma independente** e devem ser divididas: US-001, US-002, US-003, US-004, US-005 e US-007. Apenas **US-006 está adequadamente dimensionada** e não precisa de split.

O padrão mais recorrente foi **Workflow Steps** (etapas sequenciais distintas empacotadas em uma única story: configurar vs. testar, validar vs. publicar, consultar vs. reaproveitar) e **Data Variations** (tipos simples vs. tipos complexos de schema). Em nenhum caso foi necessário recorrer a Tiny Acts of Discovery — os requisitos já estão claros o suficiente para escrever stories INVEST diretamente.

Cada split abaixo foi validado contra os 5 critérios do skill: valor de usuário independente, desenvolvimento independente, teste independente, tamanho adequado a uma sprint, e soma equivalente à story original.

---

## US-001 — Configurar e testar a conexão com o Kafka corporativo

**Por que precisa de split:** a story combina duas capacidades com naturezas técnicas distintas: (1) persistir uma configuração nomeada (CRUD simples, sem rede) e (2) testar essa configuração contra um broker real (cliente Kafka, TLS, tratamento de múltiplos modos de falha). Cenário 1 é útil e revisável isoladamente — dá para cadastrar e reabrir uma configuração antes mesmo de existir um botão de teste. Os Cenários 2–4 formam uma única funcionalidade coesa de teste de conexão (sucesso, falha genérica e falha específica de certificado) e não fazem sentido separados entre si, pois "testar conexão" só entrega valor completo quando cobre também os caminhos de erro.

**Padrão aplicado:** Workflow Steps

### Split 1 de 2

## US-008

**Resumo:** Salvar e reabrir uma configuração de conexão Kafka

### Caso de Uso

- **Como um** desenvolvedor que precisa testar publicações Avro no Kafka corporativo
- **Eu quero** cadastrar e salvar uma configuração de conexão com nome, brokers, protocolo de segurança e credenciais/certificados
- **para que** eu possa reabrir e reutilizar essa configuração mais tarde, sem precisar preenchê-la novamente

### Critérios de Aceite

**Cenário 1: Salvar uma nova configuração de conexão**
- **Dado** que não existe nenhuma configuração de Kafka salva
- **Quando** o desenvolvedor preenche nome da configuração, endereço dos brokers, protocolo de segurança e credenciais/certificados aplicáveis e confirma o salvamento
- **Então** a configuração é salva localmente e pode ser reaberta posteriormente

**Requisitos Relacionados:** FR-001, FR-002, FR-003, NFR-003

### Split 2 de 2

## US-009

**Resumo:** Testar uma configuração de conexão Kafka já salva

### Caso de Uso

- **Como um** desenvolvedor que já cadastrou uma configuração de Kafka
- **Eu quero** acionar um teste de conexão contra o broker configurado
- **para que** eu tenha confiança de que a conexão está correta antes de depender dela no restante do fluxo

### Critérios de Aceite

**Cenário 1: Testar uma conexão válida**
- **Dado** uma configuração de Kafka válida e um broker acessível
- **Quando** o desenvolvedor aciona "Testar conexão"
- **Então** a ferramenta indica claramente que a conexão foi estabelecida, sem publicar nenhuma mensagem

**Cenário 2: Testar uma conexão inválida**
- **Dado** uma configuração de Kafka com um dado incorreto (broker inexistente, credencial inválida ou certificado incorreto)
- **Quando** o desenvolvedor aciona "Testar conexão"
- **Então** a ferramenta indica claramente que a conexão falhou e apresenta uma mensagem compreensível sobre o motivo

**Cenário 3: Certificado de cliente sem senha da chave privada**
- **Dado** um certificado de cliente informado sem a senha da chave privada, quando a chave exige senha
- **Quando** o desenvolvedor aciona "Testar conexão"
- **Então** o teste falha com uma mensagem que aponta especificamente esse problema

**Requisitos Relacionados:** FR-004, NFR-002, NFR-003, NFR-004, FR-026

---

## US-002 — Carregar e validar um schema Avro a partir de um arquivo .avsc

**Por que precisa de split:** exibir corretamente tipos primitivos e rejeitar arquivos malformados/semanticamente inválidos é uma funcionalidade fechada em si (Cenários 1, 2 e 4). Já o suporte a tipos compostos (union, enum, array, map, record, incluindo union opcional `["null","string"]`) do Cenário 3 é um incremento de escopo relevante — exige um formatador recursivo dedicado — e pode ser entregue, testado e revisado depois, sem bloquear o uso da ferramenta com schemas simples.

**Padrão aplicado:** Data Variations

### Split 1 de 2

## US-010

**Resumo:** Carregar e validar um schema Avro com tipos simples

### Caso de Uso

- **Como um** desenvolvedor que precisa montar mensagens Avro
- **Eu quero** carregar um arquivo `.avsc` com tipos simples e ver a ferramenta validar sua estrutura
- **para que** eu confirme que carreguei o schema correto antes de montar uma mensagem

### Critérios de Aceite

**Cenário 1: Upload de schema válido**
- **Dado** um arquivo `.avsc` válido
- **Quando** o desenvolvedor faz upload dele na tela de Schemas Avro
- **Então** a ferramenta exibe nome, namespace, lista de campos com seus tipos e o conteúdo original do schema

**Cenário 2: Upload de schema inválido**
- **Dado** um arquivo `.avsc` com uma estrutura inválida
- **Quando** o desenvolvedor tenta fazer o upload
- **Então** a ferramenta rejeita o schema e explica de forma compreensível qual é o problema

**Cenário 3: Schema sintaticamente válido mas semanticamente inválido**
- **Dado** um arquivo `.avsc` válido como JSON, mas com um tipo desconhecido ou estrutura de `record` incompleta
- **Quando** o desenvolvedor tenta fazer o upload
- **Então** a ferramenta rejeita o schema com uma explicação, sem travar nem aceitá-lo silenciosamente

**Requisitos Relacionados:** FR-008, FR-009

### Split 2 de 2

## US-011

**Resumo:** Suportar tipos complexos na exibição de um schema Avro

### Caso de Uso

- **Como um** desenvolvedor que trabalha com schemas Avro ricos
- **Eu quero** que a ferramenta exiba corretamente campos de tipos complexos ao carregar um schema
- **para que** eu confirme a estrutura completa do schema mesmo quando ele usa union, enum, array, map ou record

### Critérios de Aceite

**Cenário 1: Schema com tipos complexos**
- **Dado** um schema contendo tipos complexos (union, enum, array, map, record, incluindo um campo opcional do tipo `["null", "string"]`)
- **Quando** o schema é carregado
- **Então** todos os campos e seus tipos, incluindo os tipos compostos, são exibidos corretamente

**Requisitos Relacionados:** FR-010

---

## US-003 — Montar, validar e publicar uma mensagem Avro pela interface gráfica

**Por que precisa de split:** esta é a story mais superdimensionada do conjunto — 6 cenários cobrindo duas ações de negócio distintas e claramente sequenciais, cada uma acionada por um botão próprio ("Validar" e "Publicar"). Validar um payload contra o schema (Cenários 1, 2, 5 e 6 — compatibilidade de tipo, união opcional nula, campos extras/ausentes) já é uma funcionalidade completa e útil isoladamente, inclusive como "dry run" sem tocar o Kafka. Publicar (Cenários 3 e 4 — sucesso e falha) depende da validação, mas é uma etapa tecnicamente separada (serialização, produção real no Kafka, tratamento de erros de infraestrutura) e deve ser implementada, testada e revisada como unidade própria.

**Padrão aplicado:** Workflow Steps

### Split 1 de 2

## US-012

**Resumo:** Validar um payload Avro contra o schema carregado

### Caso de Uso

- **Como um** desenvolvedor com um schema carregado
- **Eu quero** validar um payload contra esse schema antes de publicá-lo
- **para que** eu confirme que a mensagem está correta sem precisar publicá-la no Kafka

### Critérios de Aceite

**Cenário 1: Validar payload compatível**
- **Dado** uma configuração Kafka testada e um schema carregado
- **Quando** o desenvolvedor informa um payload compatível com o schema e aciona "Validar"
- **Então** a ferramenta confirma que o payload é válido

**Cenário 2: Validar payload com tipo incompatível**
- **Dado** um payload com um campo de tipo incompatível com o schema (por exemplo, texto em um campo numérico)
- **Quando** o desenvolvedor aciona "Validar"
- **Então** a ferramenta informa qual campo está incorreto, o tipo esperado e o tipo recebido

**Cenário 3: Campo opcional recebendo valor nulo**
- **Dado** um payload contendo um campo do tipo união opcional (`["null", "string"]` ou equivalente) recebendo o valor ausente/nulo
- **Quando** o desenvolvedor aciona "Validar"
- **Então** a validação aceita corretamente tanto a ausência do valor quanto o tipo alternativo definido na união

**Cenário 4: Campos extras ou campos obrigatórios ausentes**
- **Dado** um payload contendo campos extras não previstos no schema, ou omitindo campos obrigatórios
- **Quando** o desenvolvedor aciona "Validar"
- **Então** ambos os casos são sinalizados como inválidos

**Requisitos Relacionados:** FR-011, FR-012, FR-013, FR-026

### Split 2 de 2

## US-013

**Resumo:** Publicar uma mensagem Avro validada no tópico desejado

### Caso de Uso

- **Como um** desenvolvedor com um payload validado, uma configuração Kafka testada e um tópico definido
- **Eu quero** publicar a mensagem serializada no Kafka
- **para que** eu envie uma mensagem Avro válida ao Kafka corporativo sem precisar de scripts avulsos

### Critérios de Aceite

**Cenário 1: Publicar mensagem com sucesso**
- **Dado** um payload válido, uma configuração Kafka testada, um schema carregado e um tópico informado
- **Quando** o desenvolvedor aciona "Publicar"
- **Então** a mensagem é enviada ao Kafka e a ferramenta exibe tópico, partição e offset da mensagem publicada

**Cenário 2: Falha durante a publicação**
- **Dado** uma falha durante a publicação (por exemplo, tópico inexistente ou perda de conexão)
- **Quando** o desenvolvedor aciona "Publicar"
- **Então** a ferramenta informa claramente que a publicação falhou e apresenta a mensagem de erro correspondente

**Cenário 3: Payload inválido não é publicado**
- **Dado** um payload inválido (tipo incompatível, ou com campos extras/ausentes)
- **Quando** o desenvolvedor aciona "Publicar"
- **Então** a ferramenta bloqueia a publicação e apresenta o mesmo motivo indicado pela validação, sem enviar nada ao Kafka

**Requisitos Relacionados:** FR-014, FR-015, FR-016, FR-017, FR-018, FR-026

**Nota:** esta story também deve incorporar o Cenário 5 de US-005 ("Publicação sem Schema Registry configurado") como critério de aceite adicional, já que descreve o comportamento do próprio fluxo de publicação — ver observação na seção de US-005.

---

## US-004 — Publicar uma mensagem Avro via serviço local para automações externas

**Por que precisa de split:** a operação de publicação via API local (Cenários 1–3) e a documentação interativa do serviço (Cenário 4) atendem necessidades e "atores" diferentes — uma automação externa publicando mensagens vs. um desenvolvedor explorando o serviço. A documentação pode ser entregue, testada e revisada separadamente da lógica de publicação, e não deveria bloquear nem ser bloqueada por ela.

**Padrão aplicado:** Acceptance Criteria Complexity (When distinto para um público distinto)

### Split 1 de 2

## US-014

**Resumo:** Publicar uma mensagem Avro via serviço local

### Caso de Uso

- **Como um** script ou sistema externo de automação
- **Eu quero** enviar uma requisição ao serviço local do KafkaForge informando configuração, tópico, schema e payload
- **para que** eu publique mensagens no Kafka sem depender da interface gráfica

### Critérios de Aceite

**Cenário 1: Publicação bem-sucedida via automação**
- **Dado** uma configuração e um schema já cadastrados no KafkaForge
- **Quando** uma automação externa envia um pedido de publicação informando configuração, tópico, schema e payload
- **Então** o serviço valida o payload, publica a mensagem e retorna tópico, partição e offset

**Cenário 2: Payload incompatível enviado pela automação**
- **Dado** um payload incompatível com o schema informado
- **Quando** a automação envia o pedido de publicação
- **Então** o serviço recusa a publicação e retorna uma indicação de erro compreensível, sem tentar publicar no Kafka

**Cenário 3: Configuração ou schema inexistentes**
- **Dado** uma configuração ou um schema inexistentes informados pela automação
- **Quando** o pedido é enviado
- **Então** o serviço retorna um erro indicando que a configuração ou o schema não foram encontrados

**Requisitos Relacionados:** FR-020, FR-021, NFR-006

### Split 2 de 2

## US-015

**Resumo:** Consultar a documentação interativa do serviço local

### Caso de Uso

- **Como um** desenvolvedor que integra automações ao KafkaForge
- **Eu quero** consultar uma documentação interativa das operações do serviço local
- **para que** eu entenda e teste cada operação disponível sem precisar ler o código-fonte

### Critérios de Aceite

**Cenário 1: Consultar documentação interativa do serviço**
- **Dado** o serviço local em execução
- **Quando** um desenvolvedor consulta a documentação interativa do serviço
- **Então** ele encontra a lista de operações disponíveis e consegue testar cada uma diretamente por ali

**Requisitos Relacionados:** FR-022

---

## US-005 — Configurar e testar o acesso a um Schema Registry corporativo

**Por que precisa de split:** a story mistura três preocupações: testar a conectividade do Schema Registry (Cenários 1–2, um par inseparável de sucesso/falha, análogo ao teste de conexão Kafka), navegar pelos subjects já registrados e reaproveitar um schema existente (Cenários 3–4, um fluxo de descoberta e reuso), e o comportamento de publicação quando não há Schema Registry configurado (Cenário 5, que na prática é um critério de aceite do fluxo de publicação, não da configuração do Schema Registry). Separar teste de conexão de navegação/reuso reduz o escopo técnico de cada story (cliente HTTP simples vs. lógica de listagem e deduplicação de schemas).

**Padrão aplicado:** Workflow Steps

### Split 1 de 2

## US-016

**Resumo:** Configurar e testar o acesso a um Schema Registry

### Caso de Uso

- **Como um** desenvolvedor que trabalha em um ambiente corporativo com Schema Registry
- **Eu quero** configurar e testar o acesso a um Schema Registry
- **para que** eu confirme que a ferramenta consegue se comunicar com ele antes de depender dele

### Critérios de Aceite

**Cenário 1: Testar Schema Registry acessível**
- **Dado** um Schema Registry acessível
- **Quando** o desenvolvedor informa a URL (e credenciais/certificados, se necessário) e aciona "Testar Schema Registry"
- **Então** a ferramenta confirma que o Schema Registry está acessível

**Cenário 2: Testar Schema Registry inacessível**
- **Dado** um Schema Registry inacessível ou mal configurado
- **Quando** o desenvolvedor aciona "Testar Schema Registry"
- **Então** a ferramenta informa claramente que a verificação falhou e por quê

**Requisitos Relacionados:** FR-005, FR-006, FR-007, NFR-002

### Split 2 de 2

## US-017

**Resumo:** Consultar e reaproveitar schemas já registrados no Schema Registry

### Caso de Uso

- **Como um** desenvolvedor que trabalha em um ambiente corporativo com Schema Registry
- **Eu quero** consultar os subjects já registrados e reaproveitar schemas existentes
- **para que** eu reutilize schemas existentes em vez de sempre subir um novo arquivo `.avsc`

### Critérios de Aceite

**Cenário 1: Consultar subjects existentes**
- **Dado** um Schema Registry configurado e acessível
- **Quando** o desenvolvedor consulta os subjects disponíveis
- **Então** ele visualiza a lista de subjects e consegue selecionar um schema existente em vez de fazer upload de um novo arquivo

**Cenário 2: Reaproveitar schema idêntico já registrado**
- **Dado** um schema que já existe registrado no Schema Registry
- **Quando** o desenvolvedor tenta publicar novamente um schema idêntico
- **Então** a ferramenta reaproveita o schema já registrado em vez de criar um registro duplicado

**Requisitos Relacionados:** FR-015, FR-019

**Nota:** o Cenário 5 original de US-005 ("Publicação sem Schema Registry configurado") foi realocado para US-013 (Publicar mensagem Avro validada no tópico desejado), pois descreve o comportamento do fluxo de publicação, não da configuração do Schema Registry em si.

---

## US-006 — Gerenciar múltiplas configurações de ambiente (Desenvolvimento, Homologação, Produção)

**Não precisa de split.** Os 4 cenários formam uma única capacidade coesa — gerenciar múltiplas configurações nomeadas — e nenhum dos 8 padrões de divisão se aplica de forma proveitosa:
- Não há etapas de workflow sequenciais (todos os cenários giram em torno do mesmo CRUD multi-configuração).
- Não há variações de regra de negócio ou de dado que representem fatias de valor separáveis.
- Os 4 pares Dado/Quando/Então são variações de um mesmo comportamento (isolamento entre configurações) e não fazem sentido entregues isoladamente — "criar 3 configurações" sem "editar uma sem afetar as demais" não é um incremento útil por si só.
- O escopo técnico é pequeno (é essencially uma extensão de US-008 para múltiplos registros) e cabe com folga em uma única sprint.

Nenhuma ação recomendada além de manter a dependência já natural com US-008 (Salvar e reabrir uma configuração de conexão Kafka).

---

## US-007 — Acompanhar o status atual e o histórico de operações da ferramenta

**Por que precisa de split:** a tela inicial de status (Cenário 1) e o histórico de operações (Cenários 2–3) são duas telas com fontes de dado e ciclos de vida diferentes. O status atual é uma leitura pontual do estado corrente (conexões, configuração ativa, contagem de schemas, última mensagem publicada). O histórico depende de um mecanismo de registro persistente de todas as operações (testes, validações, publicações) alimentado por várias outras stories (US-009, US-012, US-013, US-016) e inclui a investigação de falhas. São entregáveis, testáveis e revisáveis de forma independente.

**Padrão aplicado:** Workflow Steps

### Split 1 de 2

## US-018

**Resumo:** Visualizar o status atual na tela inicial

### Caso de Uso

- **Como um** desenvolvedor que usa o KafkaForge no dia a dia
- **Eu quero** visualizar rapidamente o status das conexões na tela inicial
- **para que** eu acompanhe o estado da ferramenta sem precisar examinar o código-fonte

### Critérios de Aceite

**Cenário 1: Tela inicial com status atual**
- **Dado** uma configuração ativa testada com sucesso
- **Quando** o desenvolvedor abre a tela inicial
- **Então** ele vê o status de conexão do Kafka e do Schema Registry, a configuração ativa, a quantidade de schemas carregados e os dados da última mensagem publicada

**Requisitos Relacionados:** FR-023

### Split 2 de 2

## US-019

**Resumo:** Consultar o histórico de operações e investigar falhas

### Caso de Uso

- **Como um** desenvolvedor que usa o KafkaForge no dia a dia
- **Eu quero** consultar o histórico de operações realizadas, incluindo o motivo de eventuais falhas
- **para que** eu investigue problemas sem precisar examinar o código-fonte

### Critérios de Aceite

**Cenário 1: Consultar histórico de operações**
- **Dado** operações realizadas anteriormente (testes, validações, publicações com sucesso ou falha)
- **Quando** o desenvolvedor abre a tela de histórico
- **Então** ele visualiza as operações recentes com data/hora, tipo de operação, tópico, schema, resultado e duração

**Cenário 2: Investigar uma falha pelo histórico**
- **Dado** uma operação que falhou
- **Quando** o desenvolvedor consulta o registro dessa operação no histórico
- **Então** ele encontra a mensagem de erro técnica associada, suficiente para investigar a causa

**Requisitos Relacionados:** FR-024, FR-025, FR-026

---

## Tabela-resumo

| Story original | Precisa de split? | Padrão aplicado | Novas stories |
|---|---|---|---|
| US-001 | Sim | Workflow Steps | US-008, US-009 |
| US-002 | Sim | Data Variations | US-010, US-011 |
| US-003 | Sim | Workflow Steps | US-012, US-013 |
| US-004 | Sim | Acceptance Criteria Complexity | US-014, US-015 |
| US-005 | Sim | Workflow Steps | US-016, US-017 (+ 1 critério realocado para US-013) |
| US-006 | Não | — | — |
| US-007 | Sim | Workflow Steps | US-018, US-019 |
