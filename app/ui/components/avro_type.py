from nicegui import ui

_OPTIONAL_SUFFIX = " (opcional)"
_UNION_SEPARATOR = " | "

# Cor do selo por prefixo de tipo composto — os cinco tipos compostos
# suportados por `avro/schema_loader.py` (US-002b, FR-010): union
# opcional, union genérica, enum, array, map e record.
_COMPOSITE_PREFIX_COLORS = {
    "enum<": "orange",
    "array<": "green",
    "map<": "teal",
    "record<": "indigo",
}


def _badge_color(tipo: str) -> str | None:
    if tipo.endswith(_OPTIONAL_SUFFIX):
        return "blue-grey"

    for prefixo, cor in _COMPOSITE_PREFIX_COLORS.items():
        if tipo.startswith(prefixo):
            return cor

    if _UNION_SEPARATOR in tipo:
        return "purple"

    return None


def render(tipo: str) -> None:
    """Renderiza o tipo de um campo de schema Avro já formatado por
    `avro/schema_loader.py` (US-002b) — a string em si (`tipo`) é
    inteiramente construída lá; este componente só decide *como exibi-la*.
    Tipos compostos (union opcional, union genérica, enum, array, map,
    record — FR-010) ganham um selo colorido; tipos primitivos simples
    são exibidos como texto simples. Único ponto de UI que toma essa
    decisão — reutilizado por toda tela que precise mostrar campos de um
    schema, para nunca duplicar essa lógica de apresentação entre
    páginas."""
    cor = _badge_color(tipo)
    if cor is not None:
        ui.badge(tipo, color=cor).mark("avro-type-badge")
    else:
        ui.label(tipo).mark("avro-type-label")
