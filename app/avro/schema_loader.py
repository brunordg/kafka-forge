import json
from dataclasses import dataclass

from fastavro import schema as fastavro_schema

from app.exceptions import AvroSchemaError


@dataclass
class AvroSchemaField:
    nome: str
    tipo: str


@dataclass
class LoadedAvroSchema:
    nome: str
    namespace: str | None
    fields: list[AvroSchemaField]
    raw_content: str


def _parse_json(avsc_content: str) -> dict:
    try:
        raw_schema = json.loads(avsc_content)
    except json.JSONDecodeError as error:
        raise AvroSchemaError(
            "O arquivo enviado não é um JSON válido.",
            str(error),
        ) from error

    if not isinstance(raw_schema, dict):
        raise AvroSchemaError(
            "O schema Avro deve ser um objeto JSON do tipo 'record', com 'name' e 'fields'.",
            f"Conteúdo do nível superior não é um objeto JSON: {type(raw_schema).__name__}",
        )

    return raw_schema


def _ensure_is_a_complete_record(raw_schema: dict) -> None:
    if raw_schema.get("type") != "record":
        raise AvroSchemaError(
            "O schema Avro deve ser do tipo 'record' para ser publicado no Kafka.",
            f"Campo 'type' ausente ou diferente de 'record': {raw_schema.get('type')!r}",
        )

    if not isinstance(raw_schema.get("fields"), list):
        raise AvroSchemaError(
            "A estrutura do 'record' está incompleta: é obrigatório informar a lista 'fields'.",
            f"Campo 'fields' ausente ou não é uma lista: {raw_schema.get('fields')!r}",
        )


def _validate_with_fastavro(raw_schema: dict) -> None:
    try:
        fastavro_schema.parse_schema(raw_schema)
    except Exception as error:
        # fastavro levanta tipos de exceção heterogêneos para schemas
        # semanticamente inválidos — UnknownType/SchemaParseException,
        # mas também KeyError/TypeError/AttributeError "crus" para
        # estruturas incompletas (ex.: campo sem 'name' ou sem 'type').
        # Capturamos amplamente para nunca deixar um .avsc inválido travar
        # a aplicação nem ser aceito silenciosamente (edge case da spec).
        raise AvroSchemaError(
            f"O schema Avro é inválido: {error}",
            str(error),
        ) from error


def _format_union(tipos: list) -> str:
    nao_nulos = [tipo for tipo in tipos if tipo != "null"]
    tem_nulo = len(nao_nulos) != len(tipos)

    if tem_nulo and len(nao_nulos) == 1:
        # Caso especial do campo opcional (ex.: `["null", "string"]`):
        # "string (opcional)" é bem mais legível que a união bruta.
        return f"{format_type(nao_nulos[0])} (opcional)"

    return " | ".join(format_type(tipo) for tipo in tipos)


def _format_enum(tipo: dict) -> str:
    nome = tipo.get("name", "")
    simbolos = ", ".join(tipo.get("symbols", []))
    return f"enum<{nome}>({simbolos})"


def _format_array(tipo: dict) -> str:
    return f"array<{format_type(tipo.get('items'))}>"


def _format_map(tipo: dict) -> str:
    return f"map<{format_type(tipo.get('values'))}>"


def _format_record(tipo: dict) -> str:
    nome = tipo.get("name", "")
    campos = ", ".join(
        f"{campo['name']}: {format_type(campo['type'])}" for campo in tipo.get("fields", [])
    )
    return f"record<{nome}>{{{campos}}}"


_COMPOSITE_TYPE_FORMATTERS = {
    "enum": _format_enum,
    "array": _format_array,
    "map": _format_map,
    "record": _format_record,
}


def format_type(tipo: object) -> str:
    if isinstance(tipo, str):
        # Tipo primitivo (string, int, long, float, double, boolean,
        # bytes, null) ou referência a um tipo nomeado já declarado.
        return tipo

    if isinstance(tipo, list):
        return _format_union(tipo)

    if isinstance(tipo, dict):
        formatter = _COMPOSITE_TYPE_FORMATTERS.get(tipo.get("type"))
        if formatter is not None:
            return formatter(tipo)
        if "type" in tipo:
            # Forma aninhada simples (ex.: `{"type": "string"}`,
            # logicalType) — recursão sobre o valor de "type" evita
            # duplicar a lógica acima para esse caso.
            return format_type(tipo["type"])

    # Nunca deve ocorrer para um schema já validado pelo fastavro, mas uma
    # representação bruta e segura evita travar em vez de presumir uma
    # forma específica (mesma cautela de `_validate_with_fastavro`).
    return json.dumps(tipo, ensure_ascii=False)


def _extract_fields(raw_fields: list) -> list[AvroSchemaField]:
    return [
        AvroSchemaField(nome=raw_field["name"], tipo=format_type(raw_field["type"]))
        for raw_field in raw_fields
    ]


def load_schema(avsc_content: str) -> LoadedAvroSchema:
    """Lê, valida estruturalmente e extrai nome/namespace/campos de um
    arquivo `.avsc` (US-002a/US-002b). Levanta `AvroSchemaError` tanto
    para JSON malformado quanto para uma estrutura semanticamente inválida
    como schema Avro (FR-009; cenários 2 e 3 do Acceptance Scenario de
    US-002a). Tipos compostos (union, enum, array, map, record) recebem
    uma representação recursiva legível — ver `format_type` (US-002b),
    reaproveitada por `avro/validator.py` (US-003a) para descrever o tipo
    esperado de um campo sem duplicar essa lógica de formatação."""
    raw_schema = _parse_json(avsc_content)
    _ensure_is_a_complete_record(raw_schema)
    _validate_with_fastavro(raw_schema)

    return LoadedAvroSchema(
        nome=raw_schema["name"],
        namespace=raw_schema.get("namespace"),
        fields=_extract_fields(raw_schema["fields"]),
        raw_content=avsc_content,
    )
