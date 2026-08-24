import json

import pytest

from app.avro.schema_loader import load_schema
from app.exceptions import AvroSchemaError

SIMPLE_SCHEMA = {
    "type": "record",
    "name": "Pedido",
    "namespace": "com.example",
    "fields": [
        {"name": "id", "type": "long"},
        {"name": "cliente", "type": "string"},
        {"name": "valor", "type": "double"},
        {"name": "quantidade", "type": "int"},
        {"name": "peso", "type": "float"},
        {"name": "pago", "type": "boolean"},
        {"name": "comprovante", "type": "bytes"},
    ],
}


def _content(schema: dict) -> str:
    return json.dumps(schema)


# --- cenário 1 de US-002a: .avsc válido com tipos simples ---


def test_valid_schema_with_simple_types_extracts_name_namespace_and_fields():
    result = load_schema(_content(SIMPLE_SCHEMA))

    assert result.nome == "Pedido"
    assert result.namespace == "com.example"
    assert [(f.nome, f.tipo) for f in result.fields] == [
        ("id", "long"),
        ("cliente", "string"),
        ("valor", "double"),
        ("quantidade", "int"),
        ("peso", "float"),
        ("pago", "boolean"),
        ("comprovante", "bytes"),
    ]


def test_valid_schema_preserves_the_original_raw_content():
    content = _content(SIMPLE_SCHEMA)

    result = load_schema(content)

    assert result.raw_content == content


def test_valid_schema_without_namespace_has_namespace_none():
    schema = {
        "type": "record",
        "name": "Pedido",
        "fields": [{"name": "id", "type": "long"}],
    }

    result = load_schema(_content(schema))

    assert result.namespace is None


def test_valid_schema_with_empty_fields_list_is_accepted():
    schema = {"type": "record", "name": "Vazio", "fields": []}

    result = load_schema(_content(schema))

    assert result.fields == []


# --- cenário 2 de US-002a: estrutura JSON inválida ---


def test_malformed_json_is_rejected_with_an_understandable_message():
    with pytest.raises(AvroSchemaError) as exc_info:
        load_schema('{"type": "record", "name": "Pedido", "fields": [')

    assert exc_info.value.friendly_message
    assert exc_info.value.technical_detail


def test_malformed_json_error_does_not_leak_a_raw_python_exception():
    # não deve travar nem propagar json.JSONDecodeError cru — só
    # AvroSchemaError, com detalhe técnico disponível para o histórico
    try:
        load_schema("{invalido")
    except AvroSchemaError as error:
        assert "JSON" in error.friendly_message
    else:
        pytest.fail("esperava AvroSchemaError")


# --- cenário 3 de US-002a / edge case da spec: JSON válido, Avro inválido ---


def test_top_level_json_that_is_not_an_object_is_rejected():
    with pytest.raises(AvroSchemaError):
        load_schema("[1, 2, 3]")


def test_schema_without_record_type_is_rejected():
    schema = {"type": "string"}

    with pytest.raises(AvroSchemaError) as exc_info:
        load_schema(_content(schema))

    assert "record" in exc_info.value.friendly_message.lower()


def test_record_without_fields_key_is_rejected_as_incomplete():
    schema = {"type": "record", "name": "Pedido"}

    with pytest.raises(AvroSchemaError) as exc_info:
        load_schema(_content(schema))

    assert "incompleta" in exc_info.value.friendly_message.lower()


def test_record_without_name_is_rejected():
    schema = {"type": "record", "fields": []}

    with pytest.raises(AvroSchemaError):
        load_schema(_content(schema))


def test_field_with_unknown_type_is_rejected():
    schema = {
        "type": "record",
        "name": "Pedido",
        "fields": [{"name": "id", "type": "tipo-que-nao-existe"}],
    }

    with pytest.raises(AvroSchemaError) as exc_info:
        load_schema(_content(schema))

    assert "tipo-que-nao-existe" in exc_info.value.technical_detail


def test_field_missing_type_key_is_rejected_without_crashing():
    schema = {"type": "record", "name": "Pedido", "fields": [{"name": "id"}]}

    with pytest.raises(AvroSchemaError):
        load_schema(_content(schema))


def test_field_missing_name_key_is_rejected_without_crashing():
    schema = {"type": "record", "name": "Pedido", "fields": [{"type": "string"}]}

    with pytest.raises(AvroSchemaError):
        load_schema(_content(schema))


def test_fields_that_is_not_a_list_is_rejected_as_incomplete():
    schema = {"type": "record", "name": "Pedido", "fields": "nao-e-uma-lista"}

    with pytest.raises(AvroSchemaError) as exc_info:
        load_schema(_content(schema))

    assert "incompleta" in exc_info.value.friendly_message.lower()


# --- cenário único de US-002b: os cinco tipos compostos (union, enum,
# array, map, record), incluindo o campo opcional ["null", "string"] ---

COMPLEX_SCHEMA = {
    "type": "record",
    "name": "Pedido",
    "namespace": "com.example",
    "fields": [
        {"name": "id", "type": "long"},
        {"name": "observacao", "type": ["null", "string"]},
        {
            "name": "status",
            "type": {"type": "enum", "name": "Status", "symbols": ["NOVO", "PAGO", "CANCELADO"]},
        },
        {"name": "itens", "type": {"type": "array", "items": "string"}},
        {"name": "metadados", "type": {"type": "map", "values": "string"}},
        {
            "name": "endereco",
            "type": {
                "type": "record",
                "name": "Endereco",
                "fields": [
                    {"name": "rua", "type": "string"},
                    {"name": "numero", "type": "int"},
                ],
            },
        },
    ],
}


def test_schema_with_all_five_composite_types_is_loaded_and_formatted_correctly():
    result = load_schema(_content(COMPLEX_SCHEMA))

    assert [(f.nome, f.tipo) for f in result.fields] == [
        ("id", "long"),
        ("observacao", "string (opcional)"),
        ("status", "enum<Status>(NOVO, PAGO, CANCELADO)"),
        ("itens", "array<string>"),
        ("metadados", "map<string>"),
        ("endereco", "record<Endereco>{rua: string, numero: int}"),
    ]


def test_optional_field_null_string_union_is_formatted_as_readable_not_a_raw_union():
    schema = {
        "type": "record",
        "name": "Pedido",
        "fields": [{"name": "observacao", "type": ["null", "string"]}],
    }

    result = load_schema(_content(schema))

    [campo] = result.fields
    assert campo.tipo == "string (opcional)"
    # não deve sobrar rastro da representação bruta de union (colchetes)
    assert "[" not in campo.tipo
    assert "]" not in campo.tipo


def test_optional_field_with_null_as_second_member_is_formatted_the_same_way():
    schema = {
        "type": "record",
        "name": "Pedido",
        "fields": [{"name": "observacao", "type": ["string", "null"]}],
    }

    result = load_schema(_content(schema))

    [campo] = result.fields
    assert campo.tipo == "string (opcional)"


def test_union_without_null_is_formatted_with_a_readable_separator():
    schema = {
        "type": "record",
        "name": "Pedido",
        "fields": [{"name": "quantidade", "type": ["int", "long"]}],
    }

    result = load_schema(_content(schema))

    [campo] = result.fields
    assert campo.tipo == "int | long"


def test_array_of_a_record_is_formatted_recursively():
    schema = {
        "type": "record",
        "name": "Pedido",
        "fields": [
            {
                "name": "itens",
                "type": {
                    "type": "array",
                    "items": {
                        "type": "record",
                        "name": "Item",
                        "fields": [{"name": "sku", "type": "string"}],
                    },
                },
            }
        ],
    }

    result = load_schema(_content(schema))

    [campo] = result.fields
    assert campo.tipo == "array<record<Item>{sku: string}>"
