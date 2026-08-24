from nicegui import ui

from app.services import kafka_service
from app.services.operation_log import OperationResult, OperationType
from app.ui.components import layout

ROUTE = "/logs"

_TIPO_OPTIONS = {"": "(todos)", **{tipo.value: tipo.value for tipo in OperationType}}
_RESULTADO_OPTIONS = {"": "(todos)", **{resultado.value: resultado.value for resultado in OperationResult}}


@ui.page(ROUTE)
def logs_page() -> None:
    """Histórico de operações (US-007b, FR-024/FR-025): data/hora, tipo,
    tópico, schema, resultado e duração — com filtro por tipo e por
    resultado (TASK-056). O detalhe técnico do erro (SC-007) fica
    disponível em cada linha com falha."""
    layout.render_menu()

    ui.label("Logs").classes("text-2xl font-bold")

    with ui.row().classes("items-end gap-2"):
        tipo_select = ui.select(_TIPO_OPTIONS, label="Tipo de operação", value="").mark("tipo-select")
        resultado_select = ui.select(_RESULTADO_OPTIONS, label="Resultado", value="").mark(
            "resultado-select"
        )

    rows_container = ui.column().mark("logs-table").classes("w-full gap-1")

    def _refresh() -> None:
        rows_container.clear()
        tipo = OperationType(tipo_select.value) if tipo_select.value else None
        resultado = OperationResult(resultado_select.value) if resultado_select.value else None
        records = kafka_service.list_recent_operations(tipo=tipo, resultado=resultado)

        with rows_container:
            if not records:
                ui.label("Nenhuma operação registrada ainda.").classes("text-grey").mark(
                    "logs-empty"
                )
            for index, record in enumerate(records):
                with ui.row().classes("items-center gap-3").mark(f"log-row-{index}"):
                    ui.label(record.timestamp.isoformat()).mark(f"log-timestamp-{index}")
                    ui.label(record.tipo_operacao.value).mark(f"log-tipo-{index}")
                    ui.label(record.topic or "-").mark(f"log-topic-{index}")
                    ui.label(record.schema_ or "-").mark(f"log-schema-{index}")
                    ui.label(record.resultado.value).classes(
                        "text-positive"
                        if record.resultado is OperationResult.SUCESSO
                        else "text-negative"
                    ).mark(f"log-resultado-{index}")
                    ui.label(f"{record.duracao_ms} ms").mark(f"log-duracao-{index}")
                    if record.erro_tecnico:
                        ui.label(record.erro_tecnico).classes("text-grey text-sm").mark(
                            f"log-erro-{index}"
                        )

    tipo_select.on_value_change(lambda _event: _refresh())
    resultado_select.on_value_change(lambda _event: _refresh())

    _refresh()
