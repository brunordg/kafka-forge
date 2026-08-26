from nicegui import ui

from app.services import kafka_service
from app.ui.components import layout

ROUTE = "/"


def _status_badge(connected: bool | None):
    if connected is None:
        return ui.badge("Não testado", color="grey")
    if connected:
        return ui.badge("Connected", color="positive")
    return ui.badge("Disconnected", color="negative")


def _status_card(title: str, icon: str):
    card = ui.card().classes("w-full sm:w-64 gap-1")
    with card:
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon).classes("text-primary text-xl")
            ui.label(title).classes("text-base font-medium")
    return card


@ui.page(ROUTE)
def dashboard_page() -> None:
    """Tela inicial (US-007a, FR-023): status do Kafka e do Schema
    Registry, configuração ativa, quantidade de schemas carregados e
    dados da última mensagem publicada — tudo vindo de
    `services/kafka_service.py::get_dashboard_status` (TASK-053), nunca
    calculado de novo aqui."""
    layout.render_menu(ROUTE)

    with ui.row().classes("items-center gap-2"):
        ui.icon("hub").classes("text-primary text-3xl")
        ui.label("KafkaForge").classes("text-2xl font-bold")

    status = kafka_service.get_dashboard_status()

    with ui.row().classes("w-full gap-4 items-stretch"):
        with _status_card("Kafka", "dns"):
            _status_badge(status.kafka_connected).mark("kafka-status")

        with _status_card("Schema Registry", "schema"):
            _status_badge(status.schema_registry_connected).mark("schema-registry-status")

        with _status_card("Configuração", "settings"):
            ui.label(status.active_configuration or "(nenhuma)").mark("active-configuration")

        with _status_card("Schemas carregados", "description"):
            ui.label(str(status.schemas_loaded)).classes("text-lg font-semibold").mark(
                "schemas-count"
            )

    with ui.card().classes("w-full gap-2"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("send").classes("text-primary text-xl")
            ui.label("Última mensagem publicada").classes("text-base font-medium")
        if status.last_publish_topic:
            ui.label(status.last_publish_topic).mark("last-publish-topic")
            ui.label(f"Partition: {status.last_publish_partition}").mark("last-publish-partition")
            ui.label(f"Offset: {status.last_publish_offset}").mark("last-publish-offset")
        else:
            ui.label("Nenhuma mensagem publicada ainda.").classes("text-slate-400").mark(
                "last-publish-empty"
            )
