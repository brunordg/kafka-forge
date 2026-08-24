import base64
import binascii


def _is_bytes_type(tipo: object) -> bool:
    if tipo == "bytes":
        return True
    if isinstance(tipo, list):
        return any(_is_bytes_type(item) for item in tipo)
    if isinstance(tipo, dict):
        return tipo.get("type") == "bytes"
    return False


def decode_bytes_fields(payload: dict, parsed_schema: dict) -> dict:
    """Converte campos do tipo Avro `bytes` (inclusive dentro de uma união
    opcional, ex.: `["null", "bytes"]`) de string base64 — convenção
    adotada para representar binário em JSON, que não tem tipo nativo para
    isso (FR-010, achado S2 de `analysis.md`) — para `bytes` reais, antes
    de validar ou serializar o payload. Reaproveitada por
    `avro/validator.py` e `kafka/serializer.py`, nunca duplicada entre os
    dois. Uma string que não é base64 válida é deixada como está, para que
    `avro/validator.py` a sinalize como tipo incompatível (em vez de
    escondê-la atrás de uma falha de decodificação silenciosa)."""
    decoded = dict(payload)
    for campo_schema in parsed_schema.get("fields", []):
        nome = campo_schema["name"]
        if nome not in decoded or not _is_bytes_type(campo_schema["type"]):
            continue

        valor = decoded[nome]
        if not isinstance(valor, str):
            continue

        try:
            decoded[nome] = base64.b64decode(valor, validate=True)
        except (binascii.Error, ValueError):
            continue

    return decoded
