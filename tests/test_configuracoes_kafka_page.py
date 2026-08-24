from confluent_kafka import KafkaError, KafkaException
from nicegui.elements.upload_files import SmallFileUpload

from app.config.models import EnvironmentConfiguration, KafkaConfig, SecurityProtocol
from app.services import kafka_service

ROUTE = "/configuracoes/kafka"


def _make_configuration(nome: str, bootstrap_servers: str) -> EnvironmentConfiguration:
    return EnvironmentConfiguration(
        nome=nome,
        kafka=KafkaConfig(
            bootstrap_servers=bootstrap_servers,
            security_protocol=SecurityProtocol.PLAINTEXT,
        ),
    )


class _FakeAdminClient:
    """Dublê de `AdminClient`: nunca abre um socket de verdade, então os
    testes de "Testar conexão" ficam rápidos e determinísticos sem depender
    de um Kafka real (plano, seção 12; mesma estratégia de
    `tests/test_kafka_service.py` e `tests/test_configurations_route.py`)."""

    def __init__(self, *, error: KafkaException | None = None):
        self._error = error

    def list_topics(self, timeout=None):
        if self._error is not None:
            raise self._error
        return object()


def _patch_admin_client(monkeypatch, admin_client: _FakeAdminClient) -> None:
    monkeypatch.setattr(
        kafka_service.kafka_connection, "build_admin_client", lambda configuration: admin_client
    )


def _element(user, marker: str):
    [element] = user.find(marker=marker).elements
    return element


async def test_developer_with_no_saved_configuration_can_fill_and_save(user):
    # cenário 1 do Acceptance Scenario de US-001a
    await user.open(ROUTE)
    await user.should_see("Nenhuma configuração salva ainda.")

    user.find(marker="nome-input").type("Desenvolvimento")
    user.find(marker="bootstrap-servers-input").type("localhost:9092")
    user.find(marker="save-button").click()

    await user.should_see("Configuração 'Desenvolvimento' salva com sucesso.")
    [saved] = kafka_service.list_configurations()
    assert saved.nome == "Desenvolvimento"
    assert saved.kafka.bootstrap_servers == "localhost:9092"


async def test_saved_configuration_appears_in_the_list(user):
    await user.open(ROUTE)

    user.find(marker="nome-input").type("Desenvolvimento")
    user.find(marker="bootstrap-servers-input").type("localhost:9092")
    user.find(marker="save-button").click()

    await user.should_see("Desenvolvimento — localhost:9092")
    await user.should_not_see("Nenhuma configuração salva ainda.")


async def test_saved_configuration_can_be_reopened_for_editing(user):
    await user.open(ROUTE)
    user.find(marker="nome-input").type("Desenvolvimento")
    user.find(marker="bootstrap-servers-input").type("dev-broker:9092")
    user.find(marker="save-button").click()
    await user.should_see("Configuração 'Desenvolvimento' salva com sucesso.")

    # limpa o formulário para provar que o "Editar" de fato o repreenche,
    # e não que os campos simplesmente nunca foram trocados
    user.find(marker="clear-button").click()
    assert _element(user, "nome-input").value == ""

    user.find(marker="edit-button-Desenvolvimento").click()

    assert _element(user, "nome-input").value == "Desenvolvimento"
    assert _element(user, "bootstrap-servers-input").value == "dev-broker:9092"
    await user.should_see("Editando: Desenvolvimento")


async def test_editing_and_saving_updates_the_existing_configuration_in_place(user):
    await user.open(ROUTE)
    user.find(marker="nome-input").type("Desenvolvimento")
    user.find(marker="bootstrap-servers-input").type("original:9092")
    user.find(marker="save-button").click()
    await user.should_see("Configuração 'Desenvolvimento' salva com sucesso.")

    user.find(marker="edit-button-Desenvolvimento").click()
    _element(user, "bootstrap-servers-input").value = ""
    user.find(marker="bootstrap-servers-input").type("atualizado:9092")
    user.find(marker="save-button").click()

    configurations = kafka_service.list_configurations()
    assert len(configurations) == 1
    assert configurations[0].kafka.bootstrap_servers == "atualizado:9092"


async def test_creating_a_duplicate_name_shows_a_clear_error_without_overwriting(user):
    kafka_service.create_configuration(
        _make_configuration("Desenvolvimento", "original:9092")
    )

    await user.open(ROUTE)
    user.find(marker="nome-input").type("Desenvolvimento")
    user.find(marker="bootstrap-servers-input").type("outro:9092")
    user.find(marker="save-button").click()

    await user.should_see("Já existe uma configuração chamada 'Desenvolvimento'.")
    [saved] = kafka_service.list_configurations()
    assert saved.kafka.bootstrap_servers == "original:9092"


async def test_removing_a_saved_configuration_requires_confirmation_before_deleting(user):
    # fecha a lacuna de FR-001 identificada em analysis.md, achado G1
    kafka_service.create_configuration(_make_configuration("Desenvolvimento", "localhost:9092"))

    await user.open(ROUTE)
    await user.should_see("Desenvolvimento — localhost:9092")

    user.find(marker="delete-button-Desenvolvimento").click()
    await user.should_see("Remover a configuração 'Desenvolvimento'?")

    # cancelar não remove a configuração
    user.find(marker="cancel-delete-button").click()
    await user.should_see("Desenvolvimento — localhost:9092")
    assert [c.nome for c in kafka_service.list_configurations()] == ["Desenvolvimento"]


async def test_confirming_removal_deletes_the_configuration_without_a_manual_reload(user):
    kafka_service.create_configuration(_make_configuration("Desenvolvimento", "localhost:9092"))
    kafka_service.create_configuration(_make_configuration("Homologacao", "homolog:9092"))

    await user.open(ROUTE)
    user.find(marker="delete-button-Desenvolvimento").click()
    await user.should_see("Remover a configuração 'Desenvolvimento'?")

    user.find(marker="confirm-delete-button").click()

    await user.should_see("Configuração 'Desenvolvimento' removida com sucesso.")
    await user.should_not_see("Desenvolvimento — localhost:9092")
    await user.should_see("Homologacao — homolog:9092")
    assert [c.nome for c in kafka_service.list_configurations()] == ["Homologacao"]


async def test_removing_the_configuration_currently_open_in_the_form_clears_it(user):
    kafka_service.create_configuration(_make_configuration("Desenvolvimento", "localhost:9092"))

    await user.open(ROUTE)
    user.find(marker="edit-button-Desenvolvimento").click()
    await user.should_see("Editando: Desenvolvimento")

    user.find(marker="delete-button-Desenvolvimento").click()
    user.find(marker="confirm-delete-button").click()

    await user.should_see("Configuração 'Desenvolvimento' removida com sucesso.")
    assert _element(user, "nome-input").value == ""


async def test_testing_a_valid_connection_shows_success_without_publishing_anything(
    user, monkeypatch
):
    # cenário 2 de US-001b (spec): conexão válida
    kafka_service.create_configuration(_make_configuration("Desenvolvimento", "localhost:9092"))
    admin_client = _FakeAdminClient()
    _patch_admin_client(monkeypatch, admin_client)
    build_producer_calls = []
    monkeypatch.setattr(
        kafka_service.kafka_connection,
        "build_producer",
        lambda configuration: build_producer_calls.append(configuration),
    )

    await user.open(ROUTE)
    user.find(marker="test-connection-button-Desenvolvimento").click()

    await user.should_see("Conexão com o Kafka estabelecida com sucesso.")
    assert build_producer_calls == []


async def test_testing_an_invalid_connection_shows_an_understandable_failure(user, monkeypatch):
    # cenário 3 de US-001b (spec): dado de conexão incorreto
    kafka_service.create_configuration(_make_configuration("Desenvolvimento", "localhost:9092"))
    error = KafkaException(KafkaError(KafkaError._TRANSPORT, "Simulação: broker inacessível"))
    _patch_admin_client(monkeypatch, _FakeAdminClient(error=error))

    await user.open(ROUTE)
    user.find(marker="test-connection-button-Desenvolvimento").click()

    await user.should_see("Simulação: broker inacessível")


async def test_connection_test_result_shown_in_the_ui_matches_the_api_response_shape(
    user, monkeypatch
):
    # NFR-006: o resultado exibido na tela deve ser equivalente ao
    # devolvido pela rota HTTP (TASK-018) — ambos chamam exclusivamente
    # kafka_service.test_connection e expõem a mesma `message`. Evita
    # combinar os fixtures `user` e `api_client` no mesmo teste (ver
    # comentário em tests/conftest.py sobre o singleton de `core.app`);
    # em vez disso, monta a resposta da API diretamente a partir do mesmo
    # contrato usado pela rota (`ConnectionTestResponse.from_domain`).
    from app.api.schemas.configurations import ConnectionTestResponse

    kafka_service.create_configuration(_make_configuration("Desenvolvimento", "localhost:9092"))
    error = KafkaException(KafkaError(KafkaError._TRANSPORT, "Simulação: broker inacessível"))
    _patch_admin_client(monkeypatch, _FakeAdminClient(error=error))

    api_response = ConnectionTestResponse.from_domain(
        kafka_service.test_connection("Desenvolvimento")
    )

    await user.open(ROUTE)
    user.find(marker="test-connection-button-Desenvolvimento").click()
    await user.should_see(api_response.message)


async def test_certificate_upload_is_stored_and_persisted_on_save(user):
    # FR-003: upload de certificado por arquivo
    await user.open(ROUTE)
    user.find(marker="nome-input").type("ComCertificado")
    user.find(marker="bootstrap-servers-input").type("localhost:9092")

    upload_element = _element(user, "ca-cert-upload")
    with user.client:
        await upload_element.handle_uploads([
            SmallFileUpload(
                name="ca.pem",
                content_type="application/x-pem-file",
                _data=b"-----BEGIN CERTIFICATE-----\nCONTEUDO\n-----END CERTIFICATE-----",
            )
        ])
    await user.should_see("Certificado CA carregado: ca.pem")

    user.find(marker="save-button").click()

    [saved] = kafka_service.list_configurations()
    assert saved.kafka.ca_cert == (
        "-----BEGIN CERTIFICATE-----\nCONTEUDO\n-----END CERTIFICATE-----"
    )
