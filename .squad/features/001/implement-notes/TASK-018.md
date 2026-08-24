# TASK-018 — Implementação

**Story**: US-001b
**Rota**: `POST /api/v1/configurations/{name}/test`

## O que mudou

1. **`app/api/schemas/configurations.py`**
   Adicionado o contrato `ConnectionTestResponse` (`success: bool`,
   `message: str`, `technical_detail: str = ""`), com
   `from_domain(result: ConnectionTestResult)` — mesmo padrão de
   `ConfigurationResponse.from_domain` já usado nas demais rotas —
   convertendo o dataclass `ConnectionTestResult` de
   `services/kafka_service.py` (TASK-017) no contrato HTTP.

2. **`app/api/routes/configurations.py`**
   Adicionada a rota `POST /{name}/test`, chamando exclusivamente
   `kafka_service.test_connection(name)` (nenhuma outra dependência de
   `kafka/`, `avro/` ou `config/manager.py` diretamente, verificado por
   `tests/test_architecture_boundaries.py`). Sucesso e falha de conexão
   (cenário 2 de US-001b) são ambos devolvidos com `200 OK` — a falha faz
   parte do resultado de domínio, não é um erro HTTP — enquanto
   `ConfigurationNotFoundError` (nome de configuração inexistente) vira
   `404 Not Found`, seguindo o mesmo padrão já usado em `DELETE
   /{name}` (TASK-013b).

3. **Testes — `tests/test_configurations_route.py`**
   Adicionado um dublê `_FakeAdminClient` local (mesma estratégia de
   `tests/test_kafka_service.py`/TASK-017: nunca abre socket real, testes
   rápidos e determinísticos sem depender de um Kafka corporativo real —
   plano, seção 12) e:
   - `test_test_configuration_route_returns_success_for_a_reachable_broker`
   - `test_test_configuration_route_returns_understandable_failure_for_unreachable_broker`
     (cenário 2 de US-001b: broker inexistente, via `KafkaException`
     simulada)
   - `test_test_configuration_route_for_nonexistent_configuration_returns_404`
   - `test_configurations_route_is_documented_in_openapi_schema` passou a
     também exigir `post` em `/api/v1/configurations/{name}/test`.

Nenhuma alteração foi necessária em `services/kafka_service.py` — a rota
apenas expõe `test_connection`, já implementado na TASK-017, via HTTP.

## Definition of Done — verificação

- [x] A rota retorna sucesso ou falha compreensível chamando
      exclusivamente `services/kafka_service.py` — `test_configuration`
      não importa `kafka/`, `avro/`, `registry/` nem `config.manager`
      diretamente.
- [x] A rota está documentada com `response_model` (`ConnectionTestResponse`)
      e aparece em `/docs`/`openapi.json`, confirmado por
      `test_configurations_route_is_documented_in_openapi_schema`.

## Checklist

- [x] Unit tests pass — suíte completa: `151 passed` (148 anteriores + 3
      novos testes desta task; ambiente virtual criado temporariamente
      para rodar `pytest`, removido ao final).
- [x] Integration tests pass — cobertos pelos testes de rota via
      `fastapi.testclient` (fixture `api_client`), exercitando a pilha
      completa API → `services/kafka_service.py` →
      `kafka/connection.py` → dublê de `AdminClient` (rede real
      substituída, já que não há Kafka corporativo disponível neste
      ambiente).
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado. Sanidade mínima verificada com `py_compile`.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
