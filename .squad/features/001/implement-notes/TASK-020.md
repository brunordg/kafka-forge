# TASK-020 — Implementação

**Story**: US-002a
**Classe**: `app/exceptions.py::AvroSchemaError`

## O que mudou

1. **`app/exceptions.py`**
   `AvroSchemaError` já existia na hierarquia de exceções de domínio
   (skeleton criado em uma task anterior, junto de `SchemaRegistryError`,
   `AvroValidationError`, `MessageSerializationError`, `MessagePublishError`
   etc.), como subclasse direta de `KafkaForgeError` — herdando
   automaticamente `friendly_message`/`technical_detail` (FR-026). O único
   ajuste desta task foi adicionar uma docstring explícita à classe,
   documentando:
   - o escopo (falha de estrutura de um `.avsc` — JSON sintaticamente
     válido, mas semanticamente inválido como schema Avro: tipo
     desconhecido, `record` incompleto etc., FR-009, edge case da spec);
   - a regra arquitetural de exclusividade: levantada só por
     `avro/schema_loader.py`, nunca reconstruída/duplicada em `ui/` ou
     `api/` (que apenas capturam e exibem `friendly_message`/
     `technical_detail`, seguindo o mesmo padrão já usado para
     `ConfigurationNotFoundError`/`ConfigurationAlreadyExistsError` em
     `api/routes/configurations.py` e `ui/pages/configuracoes_kafka.py`).

   Nenhuma outra alteração de comportamento: `AvroSchemaError` continua um
   subclasse simples (sem classmethods especiais), no mesmo padrão de
   `SchemaRegistryError`/`MessageSerializationError`/`MessagePublishError`
   — só `KafkaAuthenticationError` tem um classmethod dedicado
   (`missing_client_key_password`), por exigir apontar um campo específico
   (cenário 3 de US-001b); `AvroSchemaError` não tem esse requisito na
   spec, então uma fábrica dedicada seria complexidade desnecessária
   (constituição, princípio II).

2. **`app/avro/schema_loader.py`**
   Ainda não existe (só há `app/avro/.gitkeep`) — sua implementação é a
   TASK-021. Confirmado via busca em todo `app/` que `AvroSchemaError` não
   é levantada em nenhum outro ponto do código hoje, então a exclusividade
   exigida pelo DoD está trivialmente satisfeita neste momento; passa a
   ser responsabilidade de `avro/schema_loader.py`, quando implementado, a
   manter essa exclusividade.

Nenhum teste novo foi necessário: `tests/test_exceptions.py` já cobre
`AvroSchemaError` na lista parametrizada `ALL_EXCEPTION_TYPES`
(`test_exception_exposes_friendly_message_and_technical_detail` e
`test_exception_is_subclass_of_kafkaforge_error`), validando exatamente o
DoD 1 desta task.

## Definition of Done — verificação

- [x] A exceção carrega mensagem compreensível e detalhe técnico bruto
      (FR-026) — herdado de `KafkaForgeError`, confirmado pelos testes
      parametrizados já existentes em `tests/test_exceptions.py`.
- [x] É usada exclusivamente por `avro/schema_loader.py`, sem duplicar
      lógica em `ui/` ou `api/` — hoje trivialmente verdadeiro (nenhum
      raise-site existe em lugar nenhum do código ainda, já que
      `avro/schema_loader.py` é a TASK-021); a regra fica documentada na
      própria docstring da classe para orientar essa implementação futura.

## Checklist

- [x] Unit tests pass — suíte completa: `154 passed` (nenhum teste novo
      necessário; mudança é só de docstring). Ambiente virtual criado
      temporariamente para rodar `pytest`, removido ao final.
- [x] Integration tests pass — não aplicável nenhum comportamento de
      integração novo; suíte completa (incluindo os testes de
      `tests/test_exceptions.py`) permanece verde.
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
