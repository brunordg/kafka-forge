# TASK-017 — Implementação

**Story**: US-001b
**Método**: `services/kafka_service.py::test_connection`

## O que mudou

1. **`app/services/kafka_service.py`**
   - `test_connection(nome_configuracao)` deixou de ser provisório
     (`NotImplementedError`) e passou a testar a conectividade real usando
     `kafka/connection.py` (TASK-015): constrói um `AdminClient` via
     `kafka_connection.build_admin_client(configuration)` e chama
     `admin_client.list_topics(timeout=CONNECTION_TIMEOUT_MS / 1000)`.
     `list_topics` é uma chamada **somente leitura de metadados** — nunca
     instancia ou usa um `Producer`, garantindo estruturalmente NFR-002
     (nenhuma mensagem publicada, nenhum schema registrado/alterado).
   - Duas famílias de falha são tratadas e convertidas em
     `ConnectionTestResult(success=False, ...)` com mensagem compreensível
     (cenário 2 de US-001b):
     - `KafkaAuthenticationError`, levantada por
       `kafka_connection.build_client_config` (TASK-015/TASK-016) quando o
       certificado de cliente tem chave criptografada sem
       `client_key_password` — a `friendly_message`/`technical_detail` da
       própria exceção são reaproveitadas.
     - `confluent_kafka.KafkaException`, levantada por `list_topics` para
       broker inexistente, credenciais inválidas, timeout etc. Uma nova
       função `_describe_kafka_error` traduz o nome do erro `librdkafka`
       (`_TRANSPORT`, `_RESOLVE`, `_TIMED_OUT`, `_AUTHENTICATION`,
       `SASL_AUTHENTICATION_FAILED`, `_SSL`) em um prefixo em português;
       códigos sem mapeamento específico ainda produzem uma mensagem
       genérica compreensível ("Falha ao conectar ao Kafka: ..."), em vez
       de deixar o erro sem tratamento.
   - Nova função `_record_connection_test` grava o resultado (sucesso ou
     falha) como Registro de Operação via `services/operation_log.py`
     (TASK-010): `tipo_operacao=TESTE_CONEXAO`, `resultado`,
     `duracao_ms` (medido com `time.monotonic()`), `configuracao` e, em
     caso de falha, `erro_tecnico` com o detalhe técnico bruto (FR-026).
   - Novos imports: `time`, `confluent_kafka.KafkaException`,
     `app.exceptions.KafkaAuthenticationError`,
     `app.kafka.connection as kafka_connection`,
     `app.services.operation_log`. Todos consumidos exclusivamente dentro
     de `services/`, preservando a regra de que só `services/kafka_service.py`
     conhece `kafka/` (verificado por
     `tests/test_architecture_boundaries.py`, que só restringe `ui/`/`api/`).

2. **Testes — `tests/test_kafka_service.py`**
   - Adicionado um dublê `_FakeAdminClient` (nunca abre socket real) e um
     helper `_patch_admin_client`, permitindo testar sucesso/falha de forma
     rápida e determinística sem depender de um broker real — consistente
     com a estratégia de testes do plano (seção 12: testes contra um Kafka
     corporativo real ficam fora da suíte automatizada).
   - Substituídos os testes provisórios de `test_connection` (que
     esperavam `NotImplementedError`) por casos reais:
     - `test_test_connection_returns_success_for_a_reachable_broker`
     - `test_test_connection_only_reads_metadata_never_produces_a_message`
       (prova arquitetural de NFR-002: `build_producer` nunca é chamado)
     - `test_test_connection_returns_failure_for_an_unreachable_broker`
       (cenário 2: broker inexistente)
     - `test_test_connection_returns_failure_for_invalid_credentials`
       (cenário 2: credencial inválida)
     - `test_test_connection_returns_failure_for_a_client_certificate_without_key_password`
       (cenário 3: certificado incorreto)
     - `test_test_connection_records_a_successful_operation` e
       `test_test_connection_records_a_failed_operation_with_technical_detail`
       (Registro de Operação via TASK-010)
   - `test_test_connection_reads_a_fresh_snapshot_on_every_call` e
     `test_test_connection_reflects_updated_configuration_between_calls`
     foram adaptados para usar `_FakeAdminClient`/`build_admin_client`
     falso em vez de depender do antigo `NotImplementedError`, mantendo a
     garantia de leitura por snapshot (seção 11 do plano) sem tentar uma
     conexão de rede de verdade em cada chamada.
   - `test_test_connection_propagates_configuration_not_found` não precisou
     de alteração — `_get_configuration_snapshot` continua propagando
     `ConfigurationNotFoundError` antes de qualquer tentativa de conexão.

Nenhuma alteração foi necessária em `kafka/connection.py` (TASK-015),
`exceptions.py` (TASK-016) ou `services/operation_log.py` (TASK-010) — os
três já expunham exatamente o que `test_connection` precisava consumir.

## Definition of Done — verificação

- [x] Uma conexão válida retorna sucesso sem que nenhuma mensagem seja
      publicada no tópico de teste — `test_connection` nunca constrói um
      `Producer`, só um `AdminClient` para `list_topics` (metadados),
      confirmado por
      `test_test_connection_only_reads_metadata_never_produces_a_message`.
- [x] Uma conexão inválida (broker inexistente, credencial inválida,
      certificado incorreto) retorna falha com motivo compreensível
      (cenário 2 de US-001b) — os três casos têm teste dedicado.
- [x] O resultado (sucesso/falha) é gravado como Registro de Operação via
      TASK-010 — `_record_connection_test` chama
      `operation_log.append_operation_record` em todo caminho de retorno.

## Checklist

- [x] Unit tests pass — suíte completa: `148 passed` (142 anteriores + 6
      novos testes de `test_connection`, líquido de 1 teste provisório
      removido; ambiente virtual criado temporariamente para rodar
      `pytest`, removido ao final).
- [x] Integration tests pass — os testes de `test_connection` já exercitam
      a integração real entre `services/kafka_service.py`,
      `kafka/connection.py` e `services/operation_log.py` (só o socket de
      rede é substituído por um dublê, já que não há Kafka corporativo
      disponível neste ambiente; testes contra um broker real ficam fora
      da suíte automatizada por decisão do plano, seção 12).
- [ ] Typecheck passes — não aplicável: o projeto não tem mypy/pyright
      configurado (`pyproject.toml` só define
      `[tool.pytest.ini_options]`). Sanidade mínima verificada com
      `py_compile` nos arquivos alterados.
- [ ] Linter passes — não aplicável: o projeto não tem ruff/flake8
      configurado nesta etapa.
