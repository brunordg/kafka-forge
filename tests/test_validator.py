import json

from app.avro.validator import validate_payload
from app.exceptions import AvroValidationError

SCHEMA = json.dumps(
    {
        "type": "record",
        "name": "Pedido",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "cliente", "type": "string"},
            {"name": "valor", "type": "double"},
            {"name": "observacao", "type": ["null", "string"]},
        ],
    }
)


def _campos(problems: list[AvroValidationError]) -> list[str]:
    return [problem.campo for problem in problems]


# --- cenário 1 de US-003a: payload compatível é confirmado como válido ---


def test_compatible_payload_has_no_problems():
    payload = {"id": 1, "cliente": "João", "valor": 199.90, "observacao": "entrega rápida"}

    problems = validate_payload(SCHEMA, payload)

    assert problems == []


def test_compatible_payload_with_optional_field_omitted_has_no_problems():
    payload = {"id": 1, "cliente": "João", "valor": 199.90}

    problems = validate_payload(SCHEMA, payload)

    assert problems == []


# --- cenário 2 de US-003a: tipo incompatível aponta campo, tipo esperado
# e tipo recebido (FR-013) ---


def test_text_in_a_numeric_field_is_flagged_with_field_and_types():
    payload = {"id": 1, "cliente": "João", "valor": "nao-e-numero", "observacao": None}

    [problem] = validate_payload(SCHEMA, payload)

    assert problem.campo == "valor"
    assert problem.tipo_esperado == "double"
    assert problem.tipo_recebido == "string"


def test_type_mismatch_problem_is_an_avro_validation_error_with_understandable_message():
    payload = {"id": 1, "cliente": "João", "valor": "nao-e-numero", "observacao": None}

    [problem] = validate_payload(SCHEMA, payload)

    assert isinstance(problem, AvroValidationError)
    assert "valor" in problem.friendly_message
    assert "double" in problem.friendly_message
    assert "string" in problem.friendly_message


# --- cenário 3 de US-003a / edge case da spec: campo opcional
# ["null", "string"] aceita tanto ausência quanto o tipo alternativo ---


def test_optional_field_explicitly_null_is_accepted():
    payload = {"id": 1, "cliente": "João", "valor": 199.90, "observacao": None}

    problems = validate_payload(SCHEMA, payload)

    assert problems == []


def test_optional_field_with_the_alternative_type_is_accepted():
    payload = {"id": 1, "cliente": "João", "valor": 199.90, "observacao": "obs"}

    problems = validate_payload(SCHEMA, payload)

    assert problems == []


def test_optional_field_with_an_incompatible_type_is_still_flagged():
    payload = {"id": 1, "cliente": "João", "valor": 199.90, "observacao": 123}

    [problem] = validate_payload(SCHEMA, payload)

    assert problem.campo == "observacao"
    assert problem.tipo_esperado == "string (opcional)"
    assert problem.tipo_recebido == "int"


# --- cenário 4 de US-003a: campos extras e campos obrigatórios ausentes
# são ambos sinalizados como inválidos ---


def test_missing_required_field_is_flagged():
    payload = {"id": 1, "valor": 199.90}

    problems = validate_payload(SCHEMA, payload)

    assert "cliente" in _campos(problems)
    [problema_cliente] = [p for p in problems if p.campo == "cliente"]
    assert problema_cliente.tipo_esperado == "string"
    assert problema_cliente.tipo_recebido == "ausente"


def test_extra_field_not_in_schema_is_flagged():
    payload = {
        "id": 1,
        "cliente": "João",
        "valor": 199.90,
        "campo_nao_previsto": "surpresa",
    }

    problems = validate_payload(SCHEMA, payload)

    assert "campo_nao_previsto" in _campos(problems)
    [problema_extra] = [p for p in problems if p.campo == "campo_nao_previsto"]
    assert problema_extra.tipo_recebido == "string"


def test_missing_field_and_extra_field_are_both_flagged_together():
    payload = {"id": 1, "valor": 199.90, "campo_nao_previsto": "surpresa"}

    problems = validate_payload(SCHEMA, payload)

    assert set(_campos(problems)) == {"cliente", "campo_nao_previsto"}


def test_a_type_mismatch_and_an_extra_field_are_both_flagged_together():
    payload = {
        "id": 1,
        "cliente": "João",
        "valor": "nao-e-numero",
        "campo_nao_previsto": "surpresa",
    }

    problems = validate_payload(SCHEMA, payload)

    assert set(_campos(problems)) == {"valor", "campo_nao_previsto"}


def test_payload_that_is_not_a_json_object_is_flagged_instead_of_crashing():
    problems = validate_payload(SCHEMA, ["nao", "eh", "um", "objeto"])

    [problem] = problems
    assert problem.tipo_esperado == "record"
    assert problem.tipo_recebido == "array"
