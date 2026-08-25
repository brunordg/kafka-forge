import io
import json

from fastavro import schema as fastavro_schema
from fastavro import schemaless_writer

from app.avro.bytes_codec import decode_bytes_fields
from app.exceptions import MessageSerializationError

# Formato de wire da Confluent (usado quando o Schema Registry está
# configurado, US-005b/TASK-049): 1 byte mágico (sempre 0) + schema id em
# 4 bytes big-endian, antes do corpo Avro binário. Sem Schema Registry
# (FR-007), apenas o corpo Avro binário é retornado.
_MAGIC_BYTE = b"\x00"
_SCHEMA_ID_BYTES = 4


def serialize(schema_avsc: str, payload: dict, schema_id: int | None = None) -> bytes:
    """Serializa um payload já validado (`avro/validator.py`) no formato
    Avro binário compatível com o schema (US-003b, FR-014). Funciona com
    apenas o `.avsc` local (`schema_id=None`) ou, quando o Schema Registry
    está configurado, prefixado com o cabeçalho de wire da Confluent
    (`schema_id` vindo de `registry/client.py`, TASK-049) — mesma função
    para os dois casos, sem duplicar a lógica de codificação Avro."""
    try:
        parsed_schema = fastavro_schema.parse_schema(json.loads(schema_avsc))
        payload = decode_bytes_fields(payload, parsed_schema)
        buffer = io.BytesIO()
        schemaless_writer(buffer, parsed_schema, payload)
        body = buffer.getvalue()
    except Exception as error:
        raise MessageSerializationError(
            "Não foi possível serializar o payload no formato Avro binário.",
            str(error),
        ) from error

    if schema_id is None:
        return body

    return _MAGIC_BYTE + schema_id.to_bytes(_SCHEMA_ID_BYTES, byteorder="big") + body


def serialize_json(payload: dict) -> bytes:
    """Serializa um payload sem schema Avro associado — o schema é opcional
    ao publicar (schema serve para validar o payload, não para publicá-lo).
    Corpo JSON UTF-8 puro, sem cabeçalho de wire."""
    try:
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise MessageSerializationError(
            "Não foi possível serializar o payload em JSON.",
            str(error),
        ) from error
