import json

from fastavro import schema as fastavro_schema
from fastavro import validate as fastavro_validate

from app.avro.bytes_codec import decode_bytes_fields
from app.avro.schema_loader import format_type
from app.exceptions import AvroValidationError

_SEM_CAMPO_NO_SCHEMA = "(nenhum campo definido no schema)"


def _received_type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (bytes, bytearray)):
        return "bytes"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "record"
    return type(value).__name__


def _validate_known_fields(payload: dict, parsed_schema: dict) -> list[AvroValidationError]:
    problems = []
    for campo_schema in parsed_schema.get("fields", []):
        nome = campo_schema["name"]
        tipo = campo_schema["type"]
        presente = nome in payload
        valor = payload.get(nome)

        if fastavro_validate(valor, tipo, raise_errors=False):
            continue

        tipo_recebido = "ausente" if not presente else _received_type_name(valor)
        problems.append(
            AvroValidationError.field_type_mismatch(nome, format_type(tipo), tipo_recebido)
        )

    return problems


def _validate_no_extra_fields(payload: dict, parsed_schema: dict) -> list[AvroValidationError]:
    campos_definidos = {campo["name"] for campo in parsed_schema.get("fields", [])}
    return [
        AvroValidationError.field_type_mismatch(
            chave, _SEM_CAMPO_NO_SCHEMA, _received_type_name(valor)
        )
        for chave, valor in payload.items()
        if chave not in campos_definidos
    ]


def validate_payload(avsc_content: str, payload: dict) -> list[AvroValidationError]:
    """Valida um payload JSON contra um schema Avro usando
    `fastavro.validate` campo a campo (US-003a), retornando a lista
    completa de problemas encontrados — vazia quando o payload é válido.

    Diferente de `avro/schema_loader.py` (que rejeita um `.avsc` inválido
    no primeiro problema encontrado, pois ali a pergunta é "este schema
    é utilizável?"), aqui a pergunta é "o que está errado neste payload?"
    — por isso todos os problemas são coletados de uma vez, não só o
    primeiro (cenário 4: campo extra e campo obrigatório ausente podem
    coexistir no mesmo payload e devem ser sinalizados juntos).

    Cada problema aponta o campo, o tipo esperado (formatado por
    `avro/schema_loader.py::format_type`, sem duplicar essa lógica) e o
    tipo recebido (FR-013). Um campo do tipo `["null", "string"]` ausente
    ou com o valor alternativo é válido — mesma semântica nativa de
    `fastavro.validate` para uniões com `null` (cenário 3, edge case da
    spec). Campos extras não previstos no schema também são sinalizados
    (cenário 4).

    Pressupõe que `avsc_content` já é um schema estruturalmente válido
    (checado por `avro/schema_loader.py::load_schema` antes desta
    chamada) — esta função só valida o *payload* contra ele."""
    if not isinstance(payload, dict):
        return [
            AvroValidationError.field_type_mismatch(
                "(payload)", "record", _received_type_name(payload)
            )
        ]

    parsed_schema = fastavro_schema.parse_schema(json.loads(avsc_content))
    payload = decode_bytes_fields(payload, parsed_schema)

    return _validate_known_fields(payload, parsed_schema) + _validate_no_extra_fields(
        payload, parsed_schema
    )
