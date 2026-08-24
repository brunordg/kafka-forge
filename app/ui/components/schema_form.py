from typing import Callable

from nicegui import ui

_OPTIONAL_SUFFIX = " (opcional)"
_INTEGER_TYPES = {"int", "long"}
_DECIMAL_TYPES = {"float", "double"}
# Marcadores da representação já formatada por `avro/schema_loader.py::
# format_type` (union genérica, enum, array, map, record) — os mesmos que
# `ui/components/avro_type.py` usa para decidir a cor do selo. Aqui
# decidem, em vez disso, que um campo não ganha entrada própria no
# formulário automático.
_COMPLEX_MARKERS = ("<", " | ")


def _base_type(tipo: str) -> str:
    return tipo[: -len(_OPTIONAL_SUFFIX)] if tipo.endswith(_OPTIONAL_SUFFIX) else tipo


def _is_complex(tipo: str) -> bool:
    return any(marker in _base_type(tipo) for marker in _COMPLEX_MARKERS)


def render(fields: list[dict], payload: dict, on_change: Callable[[dict], None]) -> None:
    """Gera um campo de formulário por atributo do schema (FR-012,
    TASK-030b), como alternativa ao editor JSON de `publicar_mensagem.py`
    — os dois preenchem o mesmo `payload` (cada mudança no formulário
    atualiza o mesmo dicionário e, através de `on_change`, o texto do
    editor JSON), sem duplicar nenhuma lógica de validação: só
    `avro/validator.py`, via `services/kafka_service.py`, decide se o
    resultado é válido.

    Tipos compostos (union genérica, enum, array, map, record) não ganham
    campo próprio aqui — permanecem editáveis apenas pelo editor JSON,
    exatamente como o FR-012 pede ("mantendo o editor JSON disponível como
    alternativa"), em vez de reconstruir na UI a lógica de tipos que já
    vive em `avro/schema_loader.py`."""
    for campo in fields:
        nome = campo["nome"]
        tipo = campo["tipo"]
        base = _base_type(tipo)
        valor_atual = payload.get(nome)

        if _is_complex(tipo):
            ui.label(f"{nome}: editável apenas pelo editor JSON ({tipo}).").classes(
                "text-grey text-sm"
            ).mark(f"schema-form-complex-{nome}")
            continue

        if base == "boolean":

            def _handle_boolean(event, nome=nome) -> None:
                payload[nome] = event.value
                on_change(payload)

            ui.checkbox(
                nome, value=bool(valor_atual) if valor_atual is not None else False,
                on_change=_handle_boolean,
            ).mark(f"schema-form-field-{nome}")
            continue

        if base in _INTEGER_TYPES or base in _DECIMAL_TYPES:
            caster = int if base in _INTEGER_TYPES else float

            def _handle_number(event, nome=nome, caster=caster) -> None:
                payload[nome] = caster(event.value) if event.value is not None else None
                on_change(payload)

            ui.number(nome, value=valor_atual, on_change=_handle_number).mark(
                f"schema-form-field-{nome}"
            )
            continue

        def _handle_text(event, nome=nome) -> None:
            payload[nome] = event.value
            on_change(payload)

        ui.input(nome, value=str(valor_atual) if valor_atual is not None else "", on_change=_handle_text).mark(
            f"schema-form-field-{nome}"
        )
