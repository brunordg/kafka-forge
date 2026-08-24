---
stage: clarify
status: approved
sourceSkill:
  id: speckit-clarify
  version: 3f9afbb48389d08bd80f6e6bf534941572dbb101835dbb350a2c41c7710d1519
answers:
  Q1: >-
    Pode colocar a opção de colocar a Chave, mas não deve ser obrigatória, não é necessário
    especificar a partição
  Q2: O timeout deve ser de 10 segundos
  Q3: exclusivamente localhost
  Q4: >-
    pode ser ilimitado, pode persistir em um arquivo json como se fosse um log, esse arquivo deve
    ser recriado por dia
  Q5: >-
    por enquanto vamos só com usuário e senha, depois eu defino se preciso de mais tipos de
    autenticação
---

# Perguntas de Clarificação: KafkaForge — Envio de Mensagens Avro para o Kafka Corporativo

**Feature**: 001
**Especificação**: `.squad/features/001/spec.md`
**Gerado em**: 2026-08-22

As perguntas abaixo apontam áreas da especificação que ficaram subespecificadas
e que têm impacto direto na arquitetura, no modelo de dados ou nos critérios de
teste da feature. Nenhuma resposta foi presumida.

Q1: Ao publicar uma mensagem (US3/US4, FR-016), o desenvolvedor ou a automação devem poder informar uma chave (key) de mensagem e/ou uma partição específica de destino, ou toda publicação deve depender apenas do particionador padrão do Kafka sem chave?

Q2: Qual deve ser o tempo limite (timeout) concreto para as operações de "testar conexão", "testar Schema Registry" e "publicar" antes de a ferramenta considerar a operação como falha por expiração, conforme exigido de forma qualitativa pela NFR-004?

Q3: O serviço local HTTP (FR-020) deve escutar exclusivamente em `localhost`/`127.0.0.1`, ou pode ser configurado para aceitar conexões de outras máquinas na rede do desenvolvedor?

Q4: O histórico de operações (FR-024/FR-025) deve ter um limite máximo de registros retidos (por exemplo, últimas N operações) e deve persistir entre reinicializações da ferramenta, ou é aceitável um histórico ilimitado e/ou apenas em memória?

Q5: Além de usuário/senha genérico, quais mecanismos de autenticação SASL específicos (por exemplo, PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, GSSAPI/Kerberos) a configuração de Kafka (FR-002) precisa suportar explicitamente?
