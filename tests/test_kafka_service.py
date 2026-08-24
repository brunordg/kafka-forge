import pytest
from confluent_kafka import KafkaError, KafkaException

from app.config import manager as config_manager
from app.config.models import (
    EnvironmentConfiguration,
    KafkaConfig,
    SaslMechanism,
    SchemaRegistryConfig,
    SecurityProtocol,
)
from app.exceptions import (
    ConfigurationAlreadyExistsError,
    ConfigurationNotFoundError,
    SchemaNotFoundError,
    SchemaRegistryError,
)
from app.services import kafka_service, operation_log


def _configuration(nome: str, bootstrap_servers: str = "localhost:9092") -> EnvironmentConfiguration:
    return EnvironmentConfiguration(
        nome=nome,
        kafka=KafkaConfig(
            bootstrap_servers=bootstrap_servers,
            security_protocol=SecurityProtocol.PLAINTEXT,
        ),
    )


def _configuration_with_schema_registry(nome: str) -> EnvironmentConfiguration:
    configuration = _configuration(nome)
    return configuration.model_copy(
        update={"schema_registry": SchemaRegistryConfig(url="https://schema-registry.local")}
    )


class _FakeAdminClient:
    """Dublê de `AdminClient` usado nos testes de `test_connection`: nunca
    abre um socket de verdade, então os testes ficam rápidos e
    determinísticos mesmo sem um broker real disponível (plano, seção 12:
    testes que dependem de um Kafka real ficam fora da suíte automatizada)."""

    def __init__(self, *, error: KafkaException | None = None):
        self._error = error
        self.list_topics_calls: list[float | None] = []

    def list_topics(self, timeout=None):
        self.list_topics_calls.append(timeout)
        if self._error is not None:
            raise self._error
        return object()


def _patch_admin_client(monkeypatch, admin_client: _FakeAdminClient) -> None:
    monkeypatch.setattr(
        kafka_service.kafka_connection, "build_admin_client", lambda configuration: admin_client
    )


class _FakeProducer:
    """Dublê de `Producer`: entrega a mensagem sincronamente (sem socket
    real), simulando sucesso (partição/offset fixos) ou uma falha de
    delivery report — suficiente para os testes de `publish` ficarem
    rápidos e determinísticos sem depender de um broker real (plano, seção
    12)."""

    class _FakeMessage:
        def __init__(self, partition: int, offset: int):
            self._partition = partition
            self._offset = offset

        def partition(self) -> int:
            return self._partition

        def offset(self) -> int:
            return self._offset

    def __init__(self, *, error: KafkaError | None = None, partition: int = 2, offset: int = 12345):
        self._error = error
        self._partition = partition
        self._offset = offset
        self.produce_calls: list[dict] = []

    def produce(self, topic, value=None, key=None, on_delivery=None):
        self.produce_calls.append({"topic": topic, "value": value, "key": key})
        if on_delivery is not None:
            on_delivery(self._error, self._FakeMessage(self._partition, self._offset))

    def flush(self, timeout=None) -> int:
        return 0


def _patch_producer(monkeypatch, producer: _FakeProducer) -> None:
    monkeypatch.setattr(kafka_service.kafka_connection, "build_producer", lambda configuration: producer)


# --- passthroughs de configuração (US-001a, TASK-013): ui/ e api/ só
# chegam a config/manager.py através destas funções ---


def test_list_configurations_delegates_to_config_manager():
    config_manager.create_configuration(_configuration("Desenvolvimento"))

    configurations = kafka_service.list_configurations()

    assert [c.nome for c in configurations] == ["Desenvolvimento"]


def test_create_configuration_delegates_to_config_manager():
    created = kafka_service.create_configuration(_configuration("Desenvolvimento"))

    assert created.nome == "Desenvolvimento"
    assert config_manager.get_configuration("Desenvolvimento").nome == "Desenvolvimento"


def test_create_configuration_propagates_duplicate_name_error():
    kafka_service.create_configuration(_configuration("Desenvolvimento"))

    with pytest.raises(ConfigurationAlreadyExistsError):
        kafka_service.create_configuration(_configuration("Desenvolvimento"))


def test_delete_configuration_delegates_to_config_manager():
    kafka_service.create_configuration(_configuration("Desenvolvimento"))

    kafka_service.delete_configuration("Desenvolvimento")

    assert kafka_service.list_configurations() == []


def test_delete_configuration_does_not_affect_other_configurations():
    kafka_service.create_configuration(_configuration("Desenvolvimento"))
    kafka_service.create_configuration(_configuration("Homologacao", "homolog:9092"))

    kafka_service.delete_configuration("Desenvolvimento")

    assert [c.nome for c in kafka_service.list_configurations()] == ["Homologacao"]


def test_delete_configuration_propagates_configuration_not_found():
    with pytest.raises(ConfigurationNotFoundError):
        kafka_service.delete_configuration("Inexistente")


# --- test_connection (US-001b, TASK-017): sucesso, falha e ausência de
# efeitos colaterais sobre o cluster (NFR-002) ---


def test_test_connection_returns_success_for_a_reachable_broker(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    admin_client = _FakeAdminClient()
    _patch_admin_client(monkeypatch, admin_client)

    result = kafka_service.test_connection("Desenvolvimento")

    assert result.success is True
    assert "sucesso" in result.message.lower()


def test_test_connection_only_reads_metadata_never_produces_a_message(monkeypatch):
    # NFR-002: "testar conexão" não pode ter efeito colateral sobre o
    # cluster — garantimos isso arquiteturalmente usando só
    # AdminClient.list_topics, nunca um Producer.
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    admin_client = _FakeAdminClient()
    _patch_admin_client(monkeypatch, admin_client)
    build_producer_calls = []
    monkeypatch.setattr(
        kafka_service.kafka_connection,
        "build_producer",
        lambda configuration: build_producer_calls.append(configuration),
    )

    kafka_service.test_connection("Desenvolvimento")

    assert admin_client.list_topics_calls == [kafka_service.kafka_connection.CONNECTION_TIMEOUT_MS / 1000]
    assert build_producer_calls == []


def test_test_connection_returns_failure_for_an_unreachable_broker(monkeypatch):
    # cenário 2 de US-001b: broker inexistente
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    error = KafkaException(KafkaError(KafkaError._TRANSPORT, "Simulação: broker inacessível"))
    _patch_admin_client(monkeypatch, _FakeAdminClient(error=error))

    result = kafka_service.test_connection("Desenvolvimento")

    assert result.success is False
    assert "Simulação: broker inacessível" in result.message
    assert result.technical_detail == "Simulação: broker inacessível"


def test_test_connection_returns_failure_for_invalid_credentials(monkeypatch):
    # cenário 2 de US-001b: credencial inválida
    config_manager.create_configuration(
        EnvironmentConfiguration(
            nome="Desenvolvimento",
            kafka=KafkaConfig(
                bootstrap_servers="localhost:9092",
                security_protocol=SecurityProtocol.SASL_PLAINTEXT,
                sasl_mechanism=SaslMechanism.PLAIN,
                username="dev",
                password="senha-errada",
            ),
        )
    )
    error = KafkaException(
        KafkaError(KafkaError.SASL_AUTHENTICATION_FAILED, "Simulação: credenciais inválidas")
    )
    _patch_admin_client(monkeypatch, _FakeAdminClient(error=error))

    result = kafka_service.test_connection("Desenvolvimento")

    assert result.success is False
    assert "autenticação" in result.message.lower()
    assert "Simulação: credenciais inválidas" in result.message


def test_test_connection_returns_failure_for_a_client_certificate_without_key_password(monkeypatch):
    # cenário 3 de US-001b: certificado incorreto (chave criptografada sem
    # client_key_password) — detectado por kafka/connection.py (TASK-015/
    # TASK-016) antes de qualquer tentativa de conexão.
    encrypted_key = "-----BEGIN ENCRYPTED PRIVATE KEY-----\nconteudo\n-----END ENCRYPTED PRIVATE KEY-----"
    config_manager.create_configuration(
        EnvironmentConfiguration(
            nome="Desenvolvimento",
            kafka=KafkaConfig(
                bootstrap_servers="localhost:9092",
                security_protocol=SecurityProtocol.SSL,
                client_cert="cert-content",
                client_key=encrypted_key,
            ),
        )
    )

    result = kafka_service.test_connection("Desenvolvimento")

    assert result.success is False
    assert "client_key_password" in result.message


def test_test_connection_records_a_successful_operation(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    _patch_admin_client(monkeypatch, _FakeAdminClient())

    kafka_service.test_connection("Desenvolvimento")

    [record] = operation_log.read_recent_operations()
    assert record.tipo_operacao is operation_log.OperationType.TESTE_CONEXAO
    assert record.resultado is operation_log.OperationResult.SUCESSO
    assert record.configuracao == "Desenvolvimento"
    assert record.erro_tecnico is None


def test_test_connection_records_a_failed_operation_with_technical_detail(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    error = KafkaException(KafkaError(KafkaError._TRANSPORT, "Simulação: broker inacessível"))
    _patch_admin_client(monkeypatch, _FakeAdminClient(error=error))

    kafka_service.test_connection("Desenvolvimento")

    [record] = operation_log.read_recent_operations()
    assert record.resultado is operation_log.OperationResult.ERRO
    assert record.erro_tecnico == "Simulação: broker inacessível"


def test_test_schema_registry_returns_failure_when_none_is_configured():
    # FR-007: sem Schema Registry, nada deve travar — a falha é explícita
    config_manager.create_configuration(_configuration("Desenvolvimento"))

    result = kafka_service.test_schema_registry("Desenvolvimento")

    assert result.success is False
    assert "nenhum schema registry configurado" in result.message.lower()


def test_test_schema_registry_returns_success_for_an_accessible_registry(monkeypatch):
    # cenário 1 de US-005a
    config_manager.create_configuration(_configuration_with_schema_registry("Desenvolvimento"))
    monkeypatch.setattr(kafka_service.registry_client, "test_connection", lambda config: None)

    result = kafka_service.test_schema_registry("Desenvolvimento")

    assert result.success is True


def test_test_schema_registry_returns_understandable_failure(monkeypatch):
    # cenário 2 de US-005a
    config_manager.create_configuration(_configuration_with_schema_registry("Desenvolvimento"))

    def _raise(config):
        raise SchemaRegistryError("Simulação: Schema Registry inacessível", "detalhe técnico")

    monkeypatch.setattr(kafka_service.registry_client, "test_connection", _raise)

    result = kafka_service.test_schema_registry("Desenvolvimento")

    assert result.success is False
    assert result.message == "Simulação: Schema Registry inacessível"


def test_test_configuration_tests_only_kafka_when_no_schema_registry_is_configured(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    _patch_admin_client(monkeypatch, _FakeAdminClient())

    result = kafka_service.test_configuration("Desenvolvimento")

    assert result.kafka.success is True
    assert result.schema_registry is None


def test_test_configuration_tests_both_kafka_and_schema_registry_when_configured(monkeypatch):
    config_manager.create_configuration(_configuration_with_schema_registry("Desenvolvimento"))
    _patch_admin_client(monkeypatch, _FakeAdminClient())
    monkeypatch.setattr(kafka_service.registry_client, "test_connection", lambda config: None)

    result = kafka_service.test_configuration("Desenvolvimento")

    assert result.kafka.success is True
    assert result.schema_registry.success is True


# --- validate_schema (US-002a, TASK-022): delega a avro/schema_loader.py
# (TASK-021) e nunca propaga AvroSchemaError ---


def test_validate_schema_returns_a_valid_result_for_a_well_formed_avsc():
    result = kafka_service.validate_schema(
        '{"type": "record", "name": "Pedido", "namespace": "com.example", '
        '"fields": [{"name": "id", "type": "long"}]}'
    )

    assert result.valid is True
    assert result.nome == "Pedido"
    assert result.namespace == "com.example"
    assert result.fields == [{"nome": "id", "tipo": "long"}]
    assert result.raw_content is not None


def test_validate_schema_returns_an_invalid_result_instead_of_raising():
    result = kafka_service.validate_schema("{isso nao eh json valido")

    assert result.valid is False
    assert result.message
    assert result.nome is None


# --- validate_payload (US-003a, TASK-028): delega a avro/validator.py
# (TASK-027) e grava o resultado como Registro de Operação (TASK-010) ---

_PAYLOAD_SCHEMA = (
    '{"type": "record", "name": "Pedido", "fields": '
    '[{"name": "id", "type": "long"}, {"name": "valor", "type": "double"}]}'
)


def test_validate_payload_returns_valid_for_a_compatible_payload():
    result = kafka_service.validate_payload(_PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5})

    assert result.valid is True
    assert result.problems == []


def test_validate_payload_returns_problems_per_field_for_an_incompatible_payload():
    # cenário 2 de US-003a / FR-013
    result = kafka_service.validate_payload(_PAYLOAD_SCHEMA, {"id": 1, "valor": "nao-e-numero"})

    assert result.valid is False
    assert result.problems == [{"campo": "valor", "tipo_esperado": "double", "tipo_recebido": "string"}]


def test_validate_payload_returns_invalid_for_a_malformed_schema_instead_of_raising():
    result = kafka_service.validate_payload("{isso nao eh json valido", {"id": 1})

    assert result.valid is False
    assert result.message
    assert result.problems == []


def test_validate_payload_records_a_successful_operation():
    kafka_service.validate_payload(_PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5})

    [record] = operation_log.read_recent_operations()
    assert record.tipo_operacao is operation_log.OperationType.VALIDACAO_PAYLOAD
    assert record.resultado is operation_log.OperationResult.SUCESSO
    assert record.schema_ == "Pedido"
    assert record.erro_tecnico is None


def test_validate_payload_records_a_failed_operation_with_technical_detail():
    kafka_service.validate_payload(_PAYLOAD_SCHEMA, {"id": 1, "valor": "nao-e-numero"})

    [record] = operation_log.read_recent_operations()
    assert record.resultado is operation_log.OperationResult.ERRO
    assert "valor" in record.erro_tecnico
    assert "double" in record.erro_tecnico
    assert "string" in record.erro_tecnico


# --- publish (US-003b/US-004a, TASK-034): valida -> serializa -> publica
# -> registra operação; nunca reporta sucesso sem confirmação do broker ---


def test_publish_returns_success_with_partition_and_offset(monkeypatch):
    # cenário 1 do Acceptance Scenario de US-003b, FR-016/FR-017
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    _patch_producer(monkeypatch, _FakeProducer(partition=2, offset=12345))

    result = kafka_service.publish("Desenvolvimento", "pedido-criado", _PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5})

    assert result.success is True
    assert result.topic == "pedido-criado"
    assert result.partition == 2
    assert result.offset == 12345


def test_publish_works_without_a_schema_registry_using_only_the_local_avsc(monkeypatch):
    # cenário 4 do Acceptance Scenario de US-003b, FR-007/FR-014
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    assert config_manager.get_configuration("Desenvolvimento").schema_registry is None
    producer = _FakeProducer()
    _patch_producer(monkeypatch, producer)

    result = kafka_service.publish("Desenvolvimento", "pedido-criado", _PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5})

    assert result.success is True
    assert producer.produce_calls[0]["topic"] == "pedido-criado"


def test_publish_sends_the_key_when_informed(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    producer = _FakeProducer()
    _patch_producer(monkeypatch, producer)

    kafka_service.publish(
        "Desenvolvimento", "pedido-criado", _PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5}, key="123"
    )

    assert producer.produce_calls[0]["key"] == b"123"


def test_publish_blocks_an_invalid_payload_before_touching_the_producer(monkeypatch):
    # cenário 3 do Acceptance Scenario de US-003b, FR-013
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    build_producer_calls = []
    monkeypatch.setattr(
        kafka_service.kafka_connection,
        "build_producer",
        lambda configuration: build_producer_calls.append(configuration),
    )

    result = kafka_service.publish(
        "Desenvolvimento", "pedido-criado", _PAYLOAD_SCHEMA, {"id": 1, "valor": "nao-e-numero"}
    )

    assert result.success is False
    assert result.message
    assert build_producer_calls == []


def test_publish_reports_failure_for_a_nonexistent_topic(monkeypatch):
    # edge case da spec: tópico inexistente
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    error = KafkaError(KafkaError.UNKNOWN_TOPIC_OR_PART, "Simulação: tópico inexistente")
    _patch_producer(monkeypatch, _FakeProducer(error=error))

    result = kafka_service.publish("Desenvolvimento", "topico-inexistente", _PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5})

    assert result.success is False
    assert "tópico informado não existe" in result.message.lower()


def test_publish_reports_failure_when_connection_is_lost_mid_publish(monkeypatch):
    # edge case da spec: conexão perdida no meio de uma publicação — nunca
    # apresentada como sucesso sem confirmação do broker
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    error = KafkaError(KafkaError._TRANSPORT, "Simulação: conexão perdida")
    _patch_producer(monkeypatch, _FakeProducer(error=error))

    result = kafka_service.publish("Desenvolvimento", "pedido-criado", _PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5})

    assert result.success is False
    assert result.partition is None
    assert result.offset is None


def test_publish_records_a_successful_operation_with_partition_and_offset(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    _patch_producer(monkeypatch, _FakeProducer(partition=3, offset=99))

    kafka_service.publish("Desenvolvimento", "pedido-criado", _PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5}, key="k1")

    [record] = operation_log.read_recent_operations()
    assert record.tipo_operacao is operation_log.OperationType.PUBLICACAO
    assert record.resultado is operation_log.OperationResult.SUCESSO
    assert record.topic == "pedido-criado"
    assert record.partition == 3
    assert record.offset == 99
    assert record.key == "k1"


def test_publish_records_a_failed_operation_with_technical_detail(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    error = KafkaError(KafkaError.UNKNOWN_TOPIC_OR_PART, "Simulação: tópico inexistente")
    _patch_producer(monkeypatch, _FakeProducer(error=error))

    kafka_service.publish("Desenvolvimento", "topico-inexistente", _PAYLOAD_SCHEMA, {"id": 1, "valor": 10.5})

    [record] = operation_log.read_recent_operations()
    assert record.resultado is operation_log.OperationResult.ERRO
    assert "Simulação: tópico inexistente" in record.erro_tecnico


# --- schema store por nome (TASK-034b, gap identificado ao implementar
# TASK-037/TASK-038: POST /api/v1/messages referencia um schema por nome,
# o que exige um schema previamente carregado e reutilizável) ---


def test_save_schema_persists_it_for_later_retrieval_by_name():
    result = kafka_service.save_schema(_PAYLOAD_SCHEMA)

    assert result.valid is True
    retrieved = kafka_service.get_named_schema("Pedido")
    assert retrieved.nome == "Pedido"


def test_save_schema_returns_an_invalid_result_instead_of_raising_for_a_malformed_avsc():
    result = kafka_service.save_schema("{isso nao eh json valido")

    assert result.valid is False
    assert result.message


def test_get_named_schema_raises_schema_not_found_for_an_unknown_name():
    with pytest.raises(SchemaNotFoundError):
        kafka_service.get_named_schema("Inexistente")


def test_list_schema_names_reflects_saved_schemas():
    assert kafka_service.list_schema_names() == []

    kafka_service.save_schema(_PAYLOAD_SCHEMA)

    assert kafka_service.list_schema_names() == ["Pedido"]


def test_count_schemas_reflects_saved_schemas():
    assert kafka_service.count_schemas() == 0

    kafka_service.save_schema(_PAYLOAD_SCHEMA)

    assert kafka_service.count_schemas() == 1


# --- configuração inexistente: propaga o erro do config/manager.py antes
# de qualquer tentativa de orquestração ---


def test_test_connection_propagates_configuration_not_found():
    with pytest.raises(ConfigurationNotFoundError):
        kafka_service.test_connection("Inexistente")


def test_publish_propagates_configuration_not_found():
    with pytest.raises(ConfigurationNotFoundError):
        kafka_service.publish(
            "Inexistente",
            "pedido-criado",
            '{"type": "record", "name": "Pedido", "fields": []}',
            {"id": 1},
        )


# --- leitura por snapshot: cada chamada relê a Configuração de Ambiente do
# armazenamento local, sem cache/referência mutável compartilhada entre
# chamadas concorrentes de UI e API ---


def test_test_connection_reads_a_fresh_snapshot_on_every_call(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    _patch_admin_client(monkeypatch, _FakeAdminClient())
    calls = []
    original_get_configuration = config_manager.get_configuration

    def spy(nome):
        calls.append(nome)
        return original_get_configuration(nome)

    monkeypatch.setattr(kafka_service.config_manager, "get_configuration", spy)

    for _ in range(2):
        kafka_service.test_connection("Desenvolvimento")

    assert calls == ["Desenvolvimento", "Desenvolvimento"]


def test_test_connection_reflects_updated_configuration_between_calls(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento", "original:9092"))
    seen_bootstrap_servers = []

    def fake_build_admin_client(configuration):
        seen_bootstrap_servers.append(configuration.kafka.bootstrap_servers)
        return _FakeAdminClient()

    monkeypatch.setattr(
        kafka_service.kafka_connection, "build_admin_client", fake_build_admin_client
    )

    kafka_service.test_connection("Desenvolvimento")

    config_manager.update_configuration(
        "Desenvolvimento", _configuration("Desenvolvimento", "atualizado:9092")
    )

    kafka_service.test_connection("Desenvolvimento")

    assert seen_bootstrap_servers == ["original:9092", "atualizado:9092"]


def test_publish_reads_a_fresh_snapshot_on_every_call(monkeypatch):
    config_manager.create_configuration(_configuration("Desenvolvimento"))
    calls = []
    original_get_configuration = config_manager.get_configuration

    def spy(nome):
        calls.append(nome)
        return original_get_configuration(nome)

    monkeypatch.setattr(kafka_service.config_manager, "get_configuration", spy)

    for _ in range(2):
        kafka_service.publish(
            "Desenvolvimento",
            "pedido-criado",
            '{"type": "record", "name": "Pedido", "fields": []}',
            {"id": 1},
        )

    assert calls == ["Desenvolvimento", "Desenvolvimento"]
