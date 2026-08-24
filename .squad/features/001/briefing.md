---
stage: briefing
status: approved
---

# Briefing

## Problema

Enviar mensagem para o kafka corporativo

## Objetivo

Criar uma aplicação para enviar mensagens no kafka corporativo

## Contexto

Sim. Como a aplicação será **uma ferramenta local para desenvolvedores**, eu simplificaria bastante o escopo e tiraria preocupações de infraestrutura/segurança de produção. O foco passa a ser: **configurar a conexão, carregar Avro, validar, enviar para Kafka e disponibilizar uma API local para automações**.

# Briefing — KafkaForge

## Problema

Enviar mensagens Avro para o Kafka corporativo durante o desenvolvimento e testes.

Atualmente, o desenvolvedor precisa utilizar diferentes ferramentas ou criar scripts específicos para configurar a conexão com o Kafka, certificados, Schema Registry e montar/publicar mensagens Avro.

Isso torna testes e validações manuais mais trabalhosos.

## Objetivo

Criar uma aplicação local chamada **KafkaForge** para facilitar o envio de mensagens Avro para o Kafka corporativo.

A aplicação deve possuir:

1. Interface web para configuração e envio manual de mensagens.
2. Suporte a Kafka com autenticação por certificado e/ou usuário e senha.
3. Suporte a Schema Registry.
4. Upload e validação de arquivos `.avsc`.
5. Validação e edição do payload Avro.
6. Publicação de mensagens em tópicos Kafka.
7. Uma API REST local para permitir automações e integração com scripts/outros sistemas.

A aplicação será executada **localmente pelo desenvolvedor** e não será disponibilizada publicamente.

---

# Contexto

A aplicação será uma ferramenta de apoio ao desenvolvimento.

O desenvolvedor deverá conseguir abrir a aplicação localmente, configurar sua conexão com o Kafka corporativo e começar a enviar mensagens.

Fluxo principal:

```text
Desenvolvedor
      │
      ▼
   KafkaForge
      │
      ├── Configuração Kafka
      ├── Configuração Schema Registry
      ├── Certificados
      ├── Schema Avro
      └── Payload
             │
             ▼
        Serialização Avro
             │
             ▼
      Schema Registry
             │
             ▼
           Kafka
```

Também deverá ser possível utilizar a aplicação sem a interface gráfica:

```text
Script / Automação
       │
       │ HTTP
       ▼
 KafkaForge API
       │
       ▼
    Kafka
```

---

# Stack

Utilizar:

* Python 3.12+
* NiceGUI para interface web
* FastAPI para API REST
* `confluent-kafka` para comunicação com Kafka
* `fastavro` ou biblioteca equivalente para validação/serialização Avro
* Cliente do Schema Registry da Confluent quando necessário
* Pydantic para modelos e validações
* Docker/Docker Compose opcionalmente

Não utilizar:

* Node.js como backend
* React separado
* banco de dados

A aplicação deve ser simples de executar localmente.

---

# Arquitetura

Separar a aplicação em camadas:

```text
app/
├── main.py
│
├── ui/
│   ├── pages/
│   └── components/
│
├── api/
│   ├── routes/
│   └── schemas/
│
├── kafka/
│   ├── connection.py
│   ├── producer.py
│   └── serializer.py
│
├── avro/
│   ├── schema_loader.py
│   └── validator.py
│
├── registry/
│   └── client.py
│
├── config/
│   ├── models.py
│   └── manager.py
│
└── services/
    └── kafka_service.py

tests/

Dockerfile
docker-compose.yml
requirements.txt
README.md
.env.example
```

A lógica de Kafka e Avro deve ficar fora da interface NiceGUI.

---

# Configuração Kafka

Criar uma tela para configurar a conexão.

Campos:

### Identificação

* Nome da configuração

Exemplos:

```text
Desenvolvimento
Homologação
Produção
```

### Kafka

* Bootstrap Servers
* Security Protocol:

  * PLAINTEXT
  * SSL
  * SASL_PLAINTEXT
  * SASL_SSL
* SASL Mechanism:

  * PLAIN
  * SCRAM-SHA-256
  * SCRAM-SHA-512

### Credenciais

* Username
* Password

### Certificados

* CA Certificate
* Client Certificate
* Client Private Key
* Private Key Password

Os certificados devem poder ser selecionados através de upload de arquivo.

Não é necessário implementar gerenciamento avançado de secrets. A aplicação é local e voltada para desenvolvedores.

---

# Teste de conexão

Adicionar botão:

```text
[ Testar conexão ]
```

O teste deve apenas verificar se é possível conectar ao Kafka.

Não deve publicar mensagem.

Mostrar:

```text
✓ Conexão estabelecida
```

ou:

```text
✗ Falha na conexão

Mensagem:
...
```

---

# Schema Registry

Criar uma seção para configurar o Schema Registry.

Campos:

* URL
* Username
* Password
* CA Certificate
* Client Certificate
* Client Private Key

Adicionar:

```text
[ Testar Schema Registry ]
```

Permitir verificar se o Schema Registry está acessível.

A configuração do Schema Registry deve ser independente da configuração do Kafka.

---

# Schemas Avro

Criar uma tela chamada:

```text
Schemas Avro
```

Permitir fazer upload de:

```text
.avsc
```

Ao carregar um schema:

1. Ler o arquivo.
2. Validar o schema.
3. Mostrar nome.
4. Mostrar namespace.
5. Mostrar campos.
6. Mostrar tipos.
7. Mostrar o conteúdo original.
8. Informar erros caso o schema seja inválido.

Exemplo:

```text
Pedido

id          long
cliente     string
valor       double
```

---

# Payload Avro

Depois de selecionar um schema, permitir montar o payload.

Inicialmente utilizar um editor JSON:

```json
{
  "id": 123,
  "cliente": "João",
  "valor": 199.90
}
```

Adicionar:

```text
[ Validar Payload ]
```

A aplicação deve validar o JSON contra o schema Avro.

Mostrar claramente:

```text
✓ Payload válido
```

ou:

```text
✗ Payload inválido

Campo "valor":
esperado: double
recebido: string
```

---

# Formulário automático

Como melhoria, permitir gerar automaticamente um formulário baseado no Avro Schema.

Por exemplo:

Schema:

```text
id: long
cliente: string
valor: double
```

Gerar:

```text
ID
[ 123 ]

Cliente
[ João ]

Valor
[ 199.90 ]

[ Validar ]
```

O editor JSON deve continuar disponível.

---

# Tipos Avro

A implementação deve considerar:

* string
* int
* long
* float
* double
* boolean
* bytes
* null
* enum
* array
* map
* record
* union

Dar atenção especial a:

```json
["null", "string"]
```

e outros unions.

---

# Publicação Kafka

Criar uma tela:

```text
Publicar Mensagem
```

Campos:

```text
Configuração Kafka
[ Desenvolvimento ▼ ]

Topic
[ pedido-criado ]

Schema
[ Pedido ▼ ]

Payload
[ editor JSON ]
```

Botões:

```text
[ Validar ]
[ Publicar ]
```

Fluxo de publicação:

```text
Payload
   ↓
Validação Avro
   ↓
Serialização Avro
   ↓
Schema Registry
   ↓
Kafka
```

Quando publicar com sucesso, mostrar:

```text
✓ Mensagem publicada

Topic: pedido-criado
Partition: 2
Offset: 12345
```

Em caso de erro:

```text
✗ Falha ao publicar

<mensagem do erro>
```

---

# Schema Registry

Quando estiver configurado, permitir:

* Consultar subjects.
* Consultar versões.
* Selecionar schema existente.
* Visualizar schema.
* Fazer upload de novo schema.
* Registrar schema quando necessário.

Evitar registrar novamente um schema que já exista.

Caso o Schema Registry não esteja configurado, a aplicação deve permitir trabalhar diretamente com o `.avsc` e serializar a mensagem localmente.

---

# Configurações

Permitir salvar várias configurações localmente.

Exemplo:

```text
Kafka
├── Desenvolvimento
├── Homologação
└── Produção
```

Cada configuração pode conter:

```text
Kafka
├── Brokers
├── Security Protocol
├── SASL
├── Username
├── Password
├── CA
├── Client Certificate
└── Private Key

Schema Registry
├── URL
├── Username
├── Password
└── certificados
```

Não é necessário banco de dados.

Pode utilizar um arquivo local de configuração.

---

# API REST

Além da interface gráfica, disponibilizar uma API local utilizando FastAPI.

Endpoint principal:

```http
POST /api/v1/messages
```

Request:

```json
{
  "configuration": "desenvolvimento",
  "topic": "pedido-criado",
  "schema": "Pedido",
  "payload": {
    "id": 123,
    "cliente": "João",
    "valor": 199.90
  }
}
```

A aplicação deve:

1. Localizar a configuração.
2. Localizar o schema.
3. Validar o payload.
4. Serializar para Avro.
5. Utilizar o Schema Registry quando configurado.
6. Publicar no Kafka.
7. Retornar o resultado.

Response:

```json
{
  "success": true,
  "topic": "pedido-criado",
  "partition": 2,
  "offset": 12345
}
```

Erro:

```json
{
  "success": false,
  "error": "Mensagem incompatível com o schema Avro"
}
```

---

# Endpoints

Implementar:

```text
GET  /api/v1/health

GET  /api/v1/configurations

POST /api/v1/configurations

POST /api/v1/configurations/{name}/test

POST /api/v1/schema/validate

POST /api/v1/messages/validate

POST /api/v1/messages
```

Adicionar documentação automática do FastAPI.

Disponibilizar:

```text
/docs
```

para Swagger/OpenAPI.

Como a aplicação é local, não é necessário implementar neste momento um sistema complexo de autenticação da API.

---

# Dashboard

Criar uma tela inicial simples:

```text
KafkaForge

Kafka
● Connected

Schema Registry
● Connected

Configuração
Desenvolvimento

Schemas
12

Última mensagem
pedido-criado
Partition: 2
Offset: 12345
```

---

# Menu

Criar menu lateral:

```text
Dashboard

Configurações
  ├── Kafka
  └── Schema Registry

Schemas Avro

Publicar Mensagem

API

Logs
```

---

# Logs

Adicionar logs da aplicação para facilitar troubleshooting.

Registrar:

* timestamp
* operação
* topic
* schema
* partition
* offset
* sucesso/erro
* duração
* erro técnico

Como a aplicação é local, não é necessário implementar uma plataforma de observabilidade.

A tela de Logs deve permitir visualizar os logs recentes.

---

# Tratamento de erros

Criar exceções específicas:

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

A interface deve apresentar mensagens compreensíveis.

Exemplo:

```text
Não foi possível conectar ao Kafka.

Verifique:
- endereço do broker
- certificado
- usuário e senha
- protocolo de segurança
```

Não é necessário criar uma arquitetura complexa de tratamento de erros.

---

# Testes

Criar testes para:

* carregamento de `.avsc`
* validação de schema
* validação de payload
* serialização Avro
* configuração Kafka
* SSL
* SASL
* Schema Registry
* publicação
* API

Quando possível, criar testes de integração utilizando Kafka e Schema Registry em Docker.

---

# Docker

Criar:

```text
Dockerfile
docker-compose.yml
```

O Docker Compose deve subir apenas a aplicação por padrão.

Kafka e Schema Registry podem ser opcionais para ambiente de desenvolvimento.

A aplicação deve conseguir conectar em um Kafka corporativo externo.

---

# README

Criar documentação contendo:

1. Objetivo
2. Arquitetura
3. Como instalar
4. Como executar
5. Como configurar Kafka
6. Como configurar SSL
7. Como configurar mTLS
8. Como configurar SASL
9. Como configurar Schema Registry
10. Como carregar um `.avsc`
11. Como criar um payload
12. Como enviar uma mensagem
13. Como utilizar a API
14. Exemplos de `curl`
15. Exemplos de schemas Avro

---

# Requisitos de implementação

Não criar apenas um mock ou protótipo visual.

Implementar funcionalmente:

* conexão real com Kafka
* conexão real com Schema Registry
* upload real de `.avsc`
* validação real de Avro
* serialização real de Avro
* publicação real no Kafka
* API REST funcional
* interface NiceGUI funcional

O código deve ser simples, modular e fácil de manter.

Evitar overengineering.

A aplicação será executada localmente por desenvolvedores.

Não implementar neste momento:

* autenticação de usuários
* OAuth
* RBAC
* gerenciamento corporativo de secrets
* Vault
* Kubernetes
* auditoria corporativa
* banco de dados
* multi-tenancy
* observabilidade distribuída

O foco é criar uma ferramenta de desenvolvimento simples e funcional.

---

# Resultado Esperado

Uma aplicação chamada **KafkaForge** que possa ser executada localmente e permita ao desenvolvedor:

1. Configurar uma conexão com Kafka.
2. Configurar Schema Registry.
3. Informar usuário e senha quando necessário.
4. Anexar certificados quando necessário.
5. Testar a conexão.
6. Fazer upload de um `.avsc`.
7. Visualizar o schema.
8. Criar ou editar um payload.
9. Validar o payload contra o Avro.
10. Publicar a mensagem no Kafka.
11. Visualizar partition e offset retornados pelo Kafka.
12. Salvar diferentes configurações de ambientes.
13. Utilizar uma API REST local para automatizar os envios.
14. Consultar os logs da aplicação.

A experiência deve ser semelhante a uma ferramenta de desenvolvimento interna, simples de instalar, simples de configurar e simples de usar.
:::



## Resultado Esperado

Uma Aplicação capaz de enviar mensagens para o kafka corporativo com uma tela e também disponibilizar um serviço para fazer automações