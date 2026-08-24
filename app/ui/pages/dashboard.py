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


@ui.page(ROUTE)
def dashboard_page() -> None:
    """Tela inicial (US-007a, FR-023): status do Kafka e do Schema
    Registry, configuração ativa, quantidade de schemas carregados e
    dados da última mensagem publicada — tudo vindo de
    `services/kafka_service.py::get_dashboard_status` (TASK-053), nunca
    calculado de novo aqui."""
    layout.render_menu()

    ui.label("KafkaForge").classes("text-2xl font-bold")

    status = kafka_service.get_dashboard_status()

    with ui.column().classes("gap-2"):
        ui.label("Kafka").classes("text-lg")
        _status_badge(status.kafka_connected).mark("kafka-status")

        ui.label("Schema Registry").classes("text-lg")
        _status_badge(status.schema_registry_connected).mark("schema-registry-status")

        ui.label("Configuração").classes("text-lg")
        ui.label(status.active_configuration or "(nenhuma)").mark("active-configuration")

        ui.label("Schemas").classes("text-lg")
        ui.label(str(status.schemas_loaded)).mark("schemas-count")

        ui.label("Última mensagem").classes("text-lg")
        if status.last_publish_topic:
            ui.label(status.last_publish_topic).mark("last-publish-topic")
            ui.label(f"Partition: {status.last_publish_partition}").mark("last-publish-partition")
            ui.label(f"Offset: {status.last_publish_offset}").mark("last-publish-offset")
        else:
            ui.label("Nenhuma mensagem publicada ainda.").mark("last-publish-empty")
