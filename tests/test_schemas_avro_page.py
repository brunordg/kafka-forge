import json

from nicegui.elements.upload_files import SmallFileUpload

ROUTE = "/schemas/avro"

VALID_AVSC = (
    b'{"type": "record", "name": "Pedido", "namespace": "com.example", '
    b'"fields": [{"name": "id", "type": "long"}, {"name": "cliente", "type": "string"}]}'
)

INVALID_AVSC = b"{isso nao eh json valido"


def _element(user, marker: str):
    [element] = user.find(marker=marker).elements
    return element


async def _upload(user, content: bytes, name: str = "pedido.avsc") -> None:
    upload_element = _element(user, "avsc-upload")
    with user.client:
        await upload_element.handle_uploads([
            SmallFileUpload(name=name, content_type="application/json", _data=content)
        ])


async def test_uploading_a_valid_avsc_shows_name_namespace_fields_and_raw_content(user):
    # cenário 1 do Acceptance Scenario de US-002a
    await user.open(ROUTE)

    await _upload(user, VALID_AVSC)

    await user.should_see("Schema 'Pedido' válido.")
    assert _element(user, "schema-nome").text == "Nome: Pedido"
    assert _element(user, "schema-namespace").text == "Namespace: com.example"
    await user.should_see("id:")
    await user.should_see(content="long", marker="avro-type-label")
    await user.should_see("cliente:")
    await user.should_see(content="string", marker="avro-type-label")
    assert _element(user, "schema-raw-content").value == VALID_AVSC.decode()


async def test_uploading_a_valid_avsc_without_namespace_shows_a_placeholder(user):
    await user.open(ROUTE)

    await _upload(user, b'{"type": "record", "name": "Pedido", "fields": []}')

    # `should_see` faz retries com espera assíncrona, dando tempo do
    # handler de upload (agendado como tarefa em segundo plano pelo
    # NiceGUI) terminar antes de inspecionar `.text` diretamente
    await user.should_see("Schema 'Pedido' válido.")
    assert _element(user, "schema-namespace").text == "Namespace: (nenhum)"


async def test_uploading_an_invalid_avsc_shows_an_understandable_explanation(user):
    # cenário 2 do Acceptance Scenario de US-002a / FR-009
    await user.open(ROUTE)

    await _upload(user, INVALID_AVSC, name="invalido.avsc")

    await user.should_see("O arquivo enviado não é um JSON válido.")
    await user.should_not_see("Nome: Pedido")


async def test_rejected_upload_does_not_prevent_a_subsequent_valid_upload(user):
    # FR-009: rejeição não interrompe o uso das demais telas — aqui,
    # provado reutilizando o mesmo upload logo em seguida com sucesso
    await user.open(ROUTE)
    await _upload(user, INVALID_AVSC, name="invalido.avsc")
    await user.should_see("O arquivo enviado não é um JSON válido.")

    await _upload(user, VALID_AVSC)

    await user.should_see("Schema 'Pedido' válido.")
    assert _element(user, "schema-nome").text == "Nome: Pedido"


async def test_a_valid_upload_followed_by_an_invalid_one_hides_the_stale_details(user):
    await user.open(ROUTE)
    await _upload(user, VALID_AVSC)
    await user.should_see("Schema 'Pedido' válido.")

    await _upload(user, INVALID_AVSC, name="invalido.avsc")

    await user.should_see("O arquivo enviado não é um JSON válido.")
    await user.should_not_see("Nome: Pedido")


async def test_the_five_composite_types_are_rendered_via_the_shared_component(user):
    # US-002b / FR-010: union opcional, enum, array, map e record —
    # renderizados pelo componente reutilizável de
    # app/ui/components/avro_type.py, com um selo colorido em vez de
    # texto simples
    schema = {
        "type": "record",
        "name": "Pedido",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "observacao", "type": ["null", "string"]},
            {
                "name": "status",
                "type": {"type": "enum", "name": "Status", "symbols": ["NOVO", "PAGO"]},
            },
            {"name": "itens", "type": {"type": "array", "items": "string"}},
            {"name": "metadados", "type": {"type": "map", "values": "string"}},
            {
                "name": "endereco",
                "type": {
                    "type": "record",
                    "name": "Endereco",
                    "fields": [{"name": "rua", "type": "string"}],
                },
            },
        ],
    }

    await user.open(ROUTE)
    await _upload(user, json.dumps(schema).encode())

    await user.should_see("Schema 'Pedido' válido.")
    # tipo primitivo simples: texto simples, sem selo
    await user.should_see(content="long", marker="avro-type-label")
    # os cinco tipos compostos: exibidos com o selo do componente
    await user.should_see(content="string (opcional)", marker="avro-type-badge")
    await user.should_see(content="enum<Status>(NOVO, PAGO)", marker="avro-type-badge")
    await user.should_see(content="array<string>", marker="avro-type-badge")
    await user.should_see(content="map<string>", marker="avro-type-badge")
    await user.should_see(content="record<Endereco>{rua: string}", marker="avro-type-badge")
