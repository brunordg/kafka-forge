from nicegui import ui

# Menu lateral do briefing (seção "Menu"): Dashboard / Configurações
# (Kafka, Schema Registry) / Schemas Avro / Publicar Mensagem / API / Logs.
_MENU_ITEMS = [
    ("Dashboard", "/", "dashboard"),
    ("Configurações — Kafka", "/configuracoes/kafka", "config-kafka"),
    ("Configurações — Schema Registry", "/configuracoes/schema-registry", "config-schema-registry"),
    ("Schemas Avro", "/schemas/avro", "schemas-avro"),
    ("Publicar Mensagem", "/publicar-mensagem", "publicar-mensagem"),
    ("API", "/api", "api"),
    ("Logs", "/logs", "logs"),
]


def render_menu() -> None:
    """Menu lateral compartilhado por todas as telas — chamado como a
    primeira linha de cada função `@ui.page`. `ui.left_drawer` é um
    elemento de posição fixa: não precisa envolver o restante do conteúdo
    da página em um bloco `with`, então cada página continua definindo o
    resto do seu conteúdo normalmente logo em seguida."""
    with ui.left_drawer().classes("gap-1"):
        ui.label("KafkaForge").classes("text-lg font-bold")
        for label, route, slug in _MENU_ITEMS:
            ui.link(label, route).classes("block").mark(f"menu-link-{slug}")
