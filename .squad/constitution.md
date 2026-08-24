<!--
Sync Impact Report
- Version change: (nenhuma — placeholder) → 1.0.0
- Motivo do bump: MAJOR/inicial — primeira ratificação formal da constituição.
  A skill `speckit-constitution` não pôde ser executada no fluxo padrão porque
  este repositório não possui o scaffold `.specify/` (sem
  `.specify/scripts/bash/resolve-template.sh`, confirmado em
  `.squad/features/001/plan.md` e `.squad/features/001/analysis.md`). Este
  documento foi redigido manualmente, extraindo e ratificando os princípios
  que já estavam implícitos em `.squad/features/001/plan.md §2`
  ("Constitution Check" provisório) e que a análise cross-artefato
  (`analysis.md`, achado K1) confirmou estarem sendo respeitados por toda a
  arquitetura e reforçados por `tests/test_architecture_boundaries.py`.
- Princípios adicionados: I. Ferramenta Local, Sem Infraestrutura Extra;
  II. Sem Overengineering; III. Separação de Domínio e Camadas;
  IV. Paridade UI/API; V. Segurança de Segredos Locais.
- Princípios modificados: nenhum (primeira versão).
- Seções removidas: nenhuma.
- TODOs pendentes: nenhum. RATIFICATION_DATE assumida como a data desta
  ratificação por não haver registro anterior de adoção formal.
-->

# Constituição do Projeto — KafkaForge

**Versão**: 1.0.0
**Data de ratificação**: 2026-08-22
**Última emenda**: 2026-08-22

## Propósito

O KafkaForge é uma ferramenta **local, para um único desenvolvedor**, que
simplifica o envio de mensagens Avro para o Kafka corporativo durante
desenvolvimento e testes (ver `.squad/features/001/briefing.md`). Esta
constituição formaliza os princípios que já orientam as decisões de
arquitetura do projeto, para que sirvam de gate verificável em todas as
features futuras — não apenas na 001.

## Princípios

### I. Ferramenta Local, Sem Infraestrutura Extra

O KafkaForge roda inteiramente na máquina do desenvolvedor, para um único
usuário por instância. A aplicação **NÃO DEVE** introduzir banco de dados,
serviços de observabilidade distribuída, Kubernetes, Vault ou qualquer outra
peça de infraestrutura além do próprio Kafka/Schema Registry corporativos que
o usuário já está tentando alcançar.

**Rationale**: o problema que o projeto resolve é a fricção de configurar e
testar publicação Avro manualmente; adicionar infraestrutura própria
recriaria o mesmo tipo de fricção que a ferramenta existe para eliminar.

### II. Sem Overengineering

Toda solução técnica **DEVE** usar a abstração mais simples que resolve o
requisito atual. Sistemas de plugins, multi-tenancy, camadas de configuração
genéricas ou qualquer generalização especulativa para casos de uso ainda não
solicitados **NÃO DEVEM** ser adicionados.

**Rationale**: o projeto é mantido por um desenvolvedor solo para uso
próprio/time pequeno; complexidade especulativa custa mais em manutenção do
que economiza em flexibilidade futura hipotética.

### III. Separação de Domínio e Camadas (NON-NEGOTIABLE)

A lógica de domínio (`kafka/`, `avro/`, `registry/`, `config/`) **DEVE** ser
independente de framework de UI (NiceGUI) e de framework de API (FastAPI).
`ui/` e `api/` **DEVEM** consumir exclusivamente `services/` como ponto único
de orquestração — nenhuma chamada direta de `ui/` ou `api/` para
`kafka/`, `avro/`, `registry/` ou `config/` é permitida.

**Rationale**: garante que qualquer lógica de negócio testada via API também
funcione via UI (e vice-versa) sem duplicação, e mantém o domínio testável
sem subir NiceGUI/FastAPI. Esta regra já é verificada automaticamente por
`tests/test_architecture_boundaries.py`; violações **DEVEM** falhar o build.

### IV. Paridade UI/API (NFR-006)

Toda operação exposta na interface gráfica **DEVE** ter um caminho
equivalente disponível via API local (para automação por scripts), e
vice-versa. Uma feature que adiciona uma ação de domínio (ex.: criar,
editar, remover uma configuração) **NÃO ESTÁ COMPLETA** se implementar esse
caminho em apenas uma das duas camadas.

**Rationale**: o objetivo explícito do produto (`briefing.md`) inclui
"disponibilizar uma API local para automações" — paridade parcial quebra essa
promessa central do produto, não é um detalhe de polimento.

### V. Segurança de Segredos Locais

Certificados, senhas e demais segredos de conexão **DEVEM** permanecer
apenas no armazenamento local do usuário (arquivos de configuração locais) e
**NUNCA DEVEM** ser logados em texto claro, enviados a serviços de terceiros,
ou expostos fora de `127.0.0.1`. Autenticação/autorização de usuários da
própria ferramenta está fora de escopo (não há multiusuário a proteger), mas
os segredos de conexão com o Kafka corporativo **DEVEM** ser tratados como
sensíveis em todo o código.

**Rationale**: mesmo sendo uma ferramenta local sem RBAC próprio, ela guarda
credenciais de um ambiente corporativo real — o relaxamento de auth interna
não se estende ao tratamento desses segredos.

## Restrições Explicitamente Fora de Escopo

- Autenticação/RBAC de usuários da própria ferramenta.
- Multi-tenancy ou múltiplos usuários simultâneos por instância.
- Observabilidade distribuída (tracing, métricas centralizadas).
- Deploy em Kubernetes ou orquestração multi-serviço além do
  Dockerfile/docker-compose opcional já presentes no repositório.

Essas exclusões podem ser revistas em uma emenda futura, mas exigem
justificativa explícita e bump de versão MINOR ou MAJOR (ver Governança).

## Governança

- **Autoridade**: esta constituição prevalece sobre convenções implícitas em
  `plan.md` de features individuais. Em caso de conflito, o `plan.md` da
  feature **DEVE** ser corrigido para se alinhar à constituição, não o
  contrário.
- **Emendas**: qualquer alteração de princípio **DEVE** ser registrada nesta
  arquivo com um novo "Sync Impact Report" no topo, seguindo versionamento
  semântico:
  - **MAJOR**: remoção ou redefinição incompatível de um princípio existente.
  - **MINOR**: novo princípio adicionado ou princípio existente expandido
    materialmente.
  - **PATCH**: correções de redação, esclarecimentos não-semânticos.
- **Revisão de conformidade**: a cada `speckit-analyze` (ou revisão manual
  equivalente) rodado sobre uma feature, a seção "Constitution Check" do
  `plan.md` correspondente **DEVE** ser reexecutada contra a versão vigente
  desta constituição, e qualquer violação **DEVE** ser tratada como achado
  CRITICAL até ser resolvida ou formalmente aceita como exceção documentada.
- **Débito pendente conhecido**: `.squad/features/001/plan.md §2` foi escrito
  antes desta ratificação e cita a constituição como "pendente". Ele **DEVE**
  ser atualizado para referenciar a v1.0.0 na próxima revisão da feature 001
  (ver achado K1 de `.squad/features/001/analysis.md`).
