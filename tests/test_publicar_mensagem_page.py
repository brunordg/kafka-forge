from nicegui.elements.upload_files import SmallFileUpload

from app.config.models import EnvironmentConfiguration, KafkaConfig, SecurityProtocol
from app.services import kafka_service

ROUTE = "/publicar-mensagem"

SIMPLE_AVSC = (
    b'{"type": "record", "name": "Pedido", "fields": '
    b'[{"name": "id", "type": "long"}, {"name": "valor", "type": "double"}]}'
)


def _element(user, marker: str):
    [element] = user.find(marker=marker).elements
    return element


async def _upload_schema(user, content: bytes = SIMPLE_AVSC, name: str = "pedido.avsc") -> None:
    upload_element = _element(user, "schema-upload")
    with user.client:
        await upload_element.handle_uploads([
            SmallFileUpload(name=name, content_type="application/json", _data=content)
        ])
    await user.should_see(f"Schema carregado: {name}")


def _set_payload(user, text: str) -> None:
    _element(user, "payload-editor").value = text


async def test_a_valid_payload_is_confirmed_as_valid(user):
    # FR-011, FR-013
    await user.open(ROUTE)
    await _upload_schema(user)
    _set_payload(user, '{"id": 1, "valor": 199.90}')

    user.find(marker="validate-button").click()

    await user.should_see("Payload válido.")


async def test_an_invalid_payload_shows_field_expected_and_received_type_on_screen(user):
    # cenário 2 de US-003a
    await user.open(ROUTE)
    await _upload_schema(user)
    _set_payload(user, '{"id": 1, "valor": "nao-e-numero"}')

    user.find(marker="validate-button").click()

    await user.should_see("Payload inválido")
    await user.should_see("valor: esperado 'double', recebido 'string'")


async def test_malformed_payload_json_shows_an_understandable_message_without_crashing(user):
    await user.open(ROUTE)
    await _upload_schema(user)
    _set_payload(user, "{isso nao eh json valido")

    user.find(marker="validate-button").click()

    await user.should_see("O payload não é um JSON válido")


async def test_validating_without_a_schema_shows_a_guidance_message(user):
    await user.open(ROUTE)
    _set_payload(user, '{"id": 1, "valor": 199.90}')

    user.find(marker="validate-button").click()

    await user.should_see("Selecione um arquivo .avsc antes de validar.")


async def test_revalidating_after_fixing_the_payload_clears_the_previous_problems(user):
    await user.open(ROUTE)
    await _upload_schema(user)
    _set_payload(user, '{"id": 1, "valor": "nao-e-numero"}')
    user.find(marker="validate-button").click()
    await user.should_see("valor: esperado 'double', recebido 'string'")

    _set_payload(user, '{"id": 1, "valor": 199.90}')
    user.find(marker="validate-button").click()

    await user.should_see("Payload válido.")
    await user.should_not_see("valor: esperado 'double', recebido 'string'")


async def test_configuration_select_lists_saved_configurations(user):
    kafka_service.create_configuration(
        EnvironmentConfiguration(
            nome="Desenvolvimento",
            kafka=KafkaConfig(
                bootstrap_servers="localhost:9092",
                security_protocol=SecurityProtocol.PLAINTEXT,
            ),
        )
    )

    await user.open(ROUTE)

    assert _element(user, "configuration-select").options == {"Desenvolvimento": "Desenvolvimento"}
