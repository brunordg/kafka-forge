from app.ui.components.avro_type import _COMPOSITE_PREFIX_COLORS, _badge_color

# --- classificação dos cinco tipos compostos suportados (US-002b, FR-010) ---


def test_optional_union_gets_a_dedicated_badge_color():
    assert _badge_color("string (opcional)") == "blue-grey"


def test_enum_gets_a_badge_color():
    assert _badge_color("enum<Status>(NOVO, PAGO)") == _COMPOSITE_PREFIX_COLORS["enum<"]


def test_array_gets_a_badge_color():
    assert _badge_color("array<string>") == _COMPOSITE_PREFIX_COLORS["array<"]


def test_map_gets_a_badge_color():
    assert _badge_color("map<string>") == _COMPOSITE_PREFIX_COLORS["map<"]


def test_record_gets_a_badge_color():
    assert _badge_color("record<Endereco>{rua: string}") == _COMPOSITE_PREFIX_COLORS["record<"]


def test_generic_union_without_null_gets_a_badge_color():
    assert _badge_color("int | long") == "purple"


# --- tipos primitivos simples não recebem selo ---


def test_primitive_types_have_no_badge_color():
    for tipo in ("string", "int", "long", "float", "double", "boolean", "bytes", "null"):
        assert _badge_color(tipo) is None


def test_nested_composite_type_is_still_classified_by_its_own_prefix():
    # um array de record continua sendo classificado como "array" pelo
    # prefixo mais externo — a formatação recursiva em si já é
    # responsabilidade de avro/schema_loader.py (TASK-024)
    assert _badge_color("array<record<Item>{sku: string}>") == _COMPOSITE_PREFIX_COLORS["array<"]
