from app.config.models import EnvironmentConfiguration, KafkaConfig, SecurityProtocol
from app.services import kafka_service


def _element(user, marker: str):
    [element] = user.find(marker=marker).elements
    return element


async def test_dashboard_opens(user):
    await user.open("/")
    await user.should_see("KafkaForge")


async def test_dashboard_shows_data_after_operations(user):
    kafka_service.create_configuration(
        EnvironmentConfiguration(
            nome="Desenvolvimento",
            kafka=KafkaConfig(bootstrap_servers="localhost:9092", security_protocol=SecurityProtocol.PLAINTEXT),
        )
    )
    kafka_service.save_schema(
        '{"type": "record", "name": "Pedido", "fields": [{"name": "id", "type": "long"}]}'
    )

    await user.open("/")

    assert _element(user, "active-configuration").text in ("Desenvolvimento", "(nenhuma)")
    assert _element(user, "schemas-count").text == "1"


async def test_logs_opens(user):
    await user.open("/logs")
    await user.should_see("Logs")


async def test_api_page_opens(user):
    await user.open("/api")
    await user.should_see("API")
    _element(user, "docs-link")
    _element(user, "docs-iframe")


async def test_schema_registry_config_opens(user):
    await user.open("/configuracoes/schema-registry")
    await user.should_see("Schema Registry")


async def test_publicar_mensagem_schema_select_populates_form(user):
    kafka_service.save_schema(
        '{"type": "record", "name": "Pedido", "fields": '
        '[{"name": "id", "type": "long"}, {"name": "ativo", "type": "boolean"}]}'
    )

    await user.open("/publicar-mensagem")
    select = _element(user, "schema-select")
    assert select.options == {"Pedido": "Pedido"}

    select.set_value("Pedido")
    await user.should_see(marker="schema-form-field-id")
    await user.should_see(marker="schema-form-field-ativo")


async def test_schemas_avro_opens(user):
    await user.open("/schemas/avro")
    await user.should_see("Schemas Avro")


async def test_configuracoes_kafka_opens(user):
    await user.open("/configuracoes/kafka")
    await user.should_see("Configurações")


async def test_schemas_avro_registry_selector(user, monkeypatch):
    kafka_service.create_configuration(
        EnvironmentConfiguration(
            nome="Desenvolvimento",
            kafka=KafkaConfig(bootstrap_servers="localhost:9092", security_protocol=SecurityProtocol.PLAINTEXT),
        )
    )
    monkeypatch.setattr(kafka_service, "list_schema_registry_subjects", lambda nome: ["Pedido"])
    monkeypatch.setattr(
        kafka_service,
        "load_schema_from_registry",
        lambda nome, subject, version="latest": kafka_service.save_schema(
            '{"type": "record", "name": "Pedido", "fields": [{"name": "id", "type": "long"}]}'
        ),
    )

    await user.open("/schemas/avro")
    _element(user, "configuration-select").set_value("Desenvolvimento")
    await user.should_see(marker="subject-select")
    _element(user, "subject-select").set_value("Pedido")
    user.find(marker="use-registry-schema-button").click()

    await user.should_see("Schema 'Pedido' válido.")


async def test_publicar_mensagem_publish_flow(user, monkeypatch):
    kafka_service.create_configuration(
        EnvironmentConfiguration(
            nome="Desenvolvimento",
            kafka=KafkaConfig(bootstrap_servers="localhost:9092", security_protocol=SecurityProtocol.PLAINTEXT),
        )
    )

    class _FakeMessage:
        def partition(self):
            return 2

        def offset(self):
            return 12345

    class _FakeProducer:
        def produce(self, topic, value=None, key=None, on_delivery=None):
            on_delivery(None, _FakeMessage())

        def flush(self, timeout=None):
            return 0

    monkeypatch.setattr(kafka_service.kafka_connection, "build_producer", lambda configuration: _FakeProducer())

    await user.open("/publicar-mensagem")
    _element(user, "configuration-select").set_value("Desenvolvimento")
    _element(user, "topic-input").value = "pedido-criado"

    upload_element = _element(user, "schema-upload")
    from nicegui.elements.upload_files import SmallFileUpload

    with user.client:
        await upload_element.handle_uploads([
            SmallFileUpload(
                name="pedido.avsc",
                content_type="application/json",
                _data=b'{"type": "record", "name": "Pedido", "fields": [{"name": "id", "type": "long"}]}',
            )
        ])
    await user.should_see("Schema carregado: pedido.avsc")

    _element(user, "payload-editor").value = '{"id": 1}'
    user.find(marker="publish-button").click()

    await user.should_see("Mensagem publicada com sucesso.")
    await user.should_see(marker="publish-partition")
    await user.should_see(marker="publish-offset")


async def test_configuracoes_schema_registry_save_and_test(user, monkeypatch):
    kafka_service.create_configuration(
        EnvironmentConfiguration(
            nome="Desenvolvimento",
            kafka=KafkaConfig(bootstrap_servers="localhost:9092", security_protocol=SecurityProtocol.PLAINTEXT),
        )
    )
    monkeypatch.setattr(kafka_service.registry_client, "test_connection", lambda config: None)

    await user.open("/configuracoes/schema-registry")
    _element(user, "configuration-select").set_value("Desenvolvimento")
    _element(user, "url-input").value = "https://schema-registry.local"
    user.find(marker="save-button").click()
    await user.should_see("salvo com sucesso")

    saved = kafka_service.get_configuration("Desenvolvimento")
    assert saved.schema_registry.url == "https://schema-registry.local"

    user.find(marker="test-schema-registry-button").click()
    await user.should_see("Schema Registry acessível.")
