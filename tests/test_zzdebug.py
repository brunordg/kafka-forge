from nicegui.elements.upload_files import SmallFileUpload

ROUTE = "/schemas/avro"


def _element(user, marker: str):
    [element] = user.find(marker=marker).elements
    return element


async def test_debug(user):
    await user.open(ROUTE)
    upload_element = _element(user, "avsc-upload")
    with user.client:
        await upload_element.handle_uploads([
            SmallFileUpload(
                name="pedido.avsc",
                content_type="application/json",
                _data=b'{"type": "record", "name": "Pedido", "fields": []}',
            )
        ])
    status = _element(user, "status-label")
    print("STATUS TEXT:", repr(status.text))
