import base64

from fastavro import schema as fastavro_schema

from app.avro.bytes_codec import decode_bytes_fields

_SCHEMA = fastavro_schema.parse_schema(
    {
        "type": "record",
        "name": "Arquivo",
        "fields": [
            {"name": "nome", "type": "string"},
            {"name": "conteudo", "type": "bytes"},
            {"name": "assinatura", "type": ["null", "bytes"]},
        ],
    }
)


def test_decodes_a_base64_bytes_field():
    payload = {"nome": "a", "conteudo": base64.b64encode(b"binario").decode()}

    decoded = decode_bytes_fields(payload, _SCHEMA)

    assert decoded["conteudo"] == b"binario"


def test_decodes_a_base64_field_inside_an_optional_union():
    payload = {"nome": "a", "assinatura": base64.b64encode(b"sig").decode()}

    decoded = decode_bytes_fields(payload, _SCHEMA)

    assert decoded["assinatura"] == b"sig"


def test_leaves_a_missing_optional_bytes_field_untouched():
    payload = {"nome": "a"}

    decoded = decode_bytes_fields(payload, _SCHEMA)

    assert "assinatura" not in decoded


def test_leaves_non_string_values_untouched():
    payload = {"nome": "a", "conteudo": b"already-bytes"}

    decoded = decode_bytes_fields(payload, _SCHEMA)

    assert decoded["conteudo"] == b"already-bytes"


def test_leaves_an_invalid_base64_string_untouched_so_validation_can_flag_it():
    payload = {"nome": "a", "conteudo": "nao-e-base64-valido!!"}

    decoded = decode_bytes_fields(payload, _SCHEMA)

    assert decoded["conteudo"] == "nao-e-base64-valido!!"


def test_leaves_string_fields_untouched():
    payload = {"nome": "a", "conteudo": base64.b64encode(b"x").decode()}

    decoded = decode_bytes_fields(payload, _SCHEMA)

    assert decoded["nome"] == "a"
