import base64
import io
import json

import pytest
from fastavro import schema as fastavro_schema
from fastavro import schemaless_reader

from app.exceptions import MessageSerializationError
from app.kafka import serializer

SIMPLE_AVSC = (
    '{"type": "record", "name": "Pedido", "fields": '
    '[{"name": "id", "type": "long"}, {"name": "valor", "type": "double"}]}'
)


def _decode(avsc_content: str, data: bytes) -> dict:
    parsed_schema = fastavro_schema.parse_schema(json.loads(avsc_content))
    return schemaless_reader(io.BytesIO(data), parsed_schema)


def test_serialize_without_schema_id_returns_only_the_avro_binary_body():
    # FR-014, cenário 4 de US-003b: funciona só com o .avsc local
    data = serializer.serialize(SIMPLE_AVSC, {"id": 1, "valor": 10.5})

    assert _decode(SIMPLE_AVSC, data) == {"id": 1, "valor": 10.5}


def test_serialize_with_schema_id_prefixes_the_confluent_wire_format():
    data = serializer.serialize(SIMPLE_AVSC, {"id": 1, "valor": 10.5}, schema_id=42)

    assert data[0] == 0
    assert int.from_bytes(data[1:5], byteorder="big") == 42
    assert _decode(SIMPLE_AVSC, data[5:]) == {"id": 1, "valor": 10.5}


def test_serialize_raises_message_serialization_error_for_an_incompatible_payload():
    with pytest.raises(MessageSerializationError):
        serializer.serialize(SIMPLE_AVSC, {"id": "nao-e-numero", "valor": 10.5})


def test_serialize_json_returns_the_payload_as_utf8_json_bytes():
    # schema Avro é opcional ao publicar: sem ele, o payload vira JSON puro
    data = serializer.serialize_json({"id": 1, "valor": 10.5})

    assert json.loads(data.decode("utf-8")) == {"id": 1, "valor": 10.5}


def test_serialize_decodes_base64_bytes_fields():
    # S2 de analysis.md: campos `bytes` são representados em base64 no JSON
    avsc = '{"type": "record", "name": "Arquivo", "fields": [{"name": "conteudo", "type": "bytes"}]}'
    payload = {"conteudo": base64.b64encode(b"conteudo binario").decode()}

    data = serializer.serialize(avsc, payload)

    assert _decode(avsc, data) == {"conteudo": b"conteudo binario"}
