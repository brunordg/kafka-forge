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
    layout.render_menu(ROUTE)

    with ui.row().classes("items-center gap-2"):
        ui.icon("history").classes("text-primary text-3xl")
        ui.label("Logs").classes("text-2xl font-bold")

    with ui.card().classes("w-full"):
        with ui.row().classes("items-end gap-2"):
            tipo_select = (
                ui.select(_TIPO_OPTIONS, label="Tipo de operação", value="")
                .props("outlined dense")
                .classes("w-56")
                .mark("tipo-select")
            )
            resultado_select = (
                ui.select(_RESULTADO_OPTIONS, label="Resultado", value="")
                .props("outlined dense")
                .classes("w-56")
                .mark("resultado-select")
            )

    rows_container = ui.column().mark("logs-table").classes("w-full gap-2")

    def _refresh() -> None:
        rows_container.clear()
        tipo = OperationType(tipo_select.value) if tipo_select.value else None
        resultado = OperationResult(resultado_select.value) if resultado_select.value else None
        records = kafka_service.list_recent_operations(tipo=tipo, resultado=resultado)

        with rows_container:
            if not records:
                with ui.card().classes("w-full items-center py-6"):
                    ui.icon("inbox").classes("text-3xl text-slate-300")
                    ui.label("Nenhuma operação registrada ainda.").classes("text-slate-400").mark(
                        "logs-empty"
                    )
            for index, record in enumerate(records):
                sucesso = record.resultado is OperationResult.SUCESSO
                with ui.card().classes("w-full py-2 px-4"):
                    with ui.row().classes("items-center gap-3 w-full").mark(f"log-row-{index}"):
                        ui.icon("check_circle" if sucesso else "cancel").classes(
                            "text-positive" if sucesso else "text-negative"
                        )
                        ui.label(record.timestamp.isoformat()).classes(
                            "text-slate-400 text-sm w-44"
                        ).mark(f"log-timestamp-{index}")
                        ui.badge(record.tipo_operacao.value, color="secondary").mark(
                            f"log-tipo-{index}"
                        )
                        ui.label(record.topic or "-").classes("font-medium").mark(
                            f"log-topic-{index}"
                        )
                        ui.label(record.schema_ or "-").classes("text-slate-500").mark(
                            f"log-schema-{index}"
                        )
                        ui.label(record.resultado.value).classes(
                            "text-positive font-medium" if sucesso else "text-negative font-medium"
                        ).mark(f"log-resultado-{index}")
                        ui.label(f"{record.duracao_ms} ms").classes(
                            "text-slate-400 text-sm ml-auto"
                        ).mark(f"log-duracao-{index}")
                    if record.erro_tecnico:
                        ui.label(record.erro_tecnico).classes("text-grey text-sm").mark(
                            f"log-erro-{index}"
                        )

    tipo_select.on_value_change(lambda _event: _refresh())
    resultado_select.on_value_change(lambda _event: _refresh())

    _refresh()
