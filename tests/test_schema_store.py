import pytest

from app.avro import schema_store
from app.avro.schema_loader import load_schema
from app.exceptions import SchemaNotFoundError

SIMPLE_AVSC = (
    '{"type": "record", "name": "Pedido", "fields": '
    '[{"name": "id", "type": "long"}, {"name": "valor", "type": "double"}]}'
)


def test_save_and_get_schema_round_trips_by_name():
    schema_store.save_schema(load_schema(SIMPLE_AVSC))

    retrieved = schema_store.get_schema("Pedido")

    assert retrieved.nome == "Pedido"
    assert retrieved.fields[0].nome == "id"


def test_get_unknown_schema_raises_schema_not_found():
    with pytest.raises(SchemaNotFoundError) as exc_info:
        schema_store.get_schema("Inexistente")

    assert "Inexistente" in exc_info.value.friendly_message


def test_list_schemas_reflects_saved_schemas():
    assert schema_store.list_schemas() == []

    schema_store.save_schema(load_schema(SIMPLE_AVSC))

    [loaded] = schema_store.list_schemas()
    assert loaded.nome == "Pedido"


def test_saving_the_same_name_twice_overwrites_instead_of_duplicating():
    schema_store.save_schema(load_schema(SIMPLE_AVSC))
    updated_avsc = (
        '{"type": "record", "name": "Pedido", "fields": [{"name": "id", "type": "long"}]}'
    )

    schema_store.save_schema(load_schema(updated_avsc))

    assert schema_store.count_schemas() == 1
    assert len(schema_store.get_schema("Pedido").fields) == 1


def test_count_schemas_reflects_saved_schemas():
    assert schema_store.count_schemas() == 0

    schema_store.save_schema(load_schema(SIMPLE_AVSC))

    assert schema_store.count_schemas() == 1
