from nicegui import ui

# Menu lateral do briefing (seção "Menu"): Dashboard / Configurações
# (Kafka, Schema Registry) / Schemas Avro / Publicar Mensagem / API / Logs.
_MENU_ITEMS = [
    ("Dashboard", "/", "dashboard", "space_dashboard"),
    ("Configurações — Kafka", "/configuracoes/kafka", "config-kafka", "dns"),
    ("Configurações — Schema Registry", "/configuracoes/schema-registry", "config-schema-registry", "schema"),
    ("Schemas Avro", "/schemas/avro", "schemas-avro", "description"),
    ("Publicar Mensagem", "/publicar-mensagem", "publicar-mensagem", "send"),
    ("API", "/api", "api", "api"),
    ("Logs", "/logs", "logs", "history"),
]

def render_menu(current_route: str = "") -> None:
    """Header + menu lateral compartilhados por todas as telas — chamado
    como a primeira linha de cada função `@ui.page`, passando a própria
    `ROUTE` da página para destacar o item ativo. `ui.header`/`ui.left_drawer`
    são elementos de posição fixa: não precisam envolver o restante do
    conteúdo da página em um bloco `with`, então cada página continua
    definindo o resto do seu conteúdo normalmente logo em seguida."""
    dark_mode = ui.dark_mode()

    drawer = ui.left_drawer().classes("bg-slate-50 dark:bg-slate-900 gap-1 p-2")

    with ui.header().classes("items-center justify-between bg-primary text-white shadow-md"):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="menu", on_click=drawer.toggle).props("flat round dense color=white")
            ui.icon("hub").classes("text-2xl")
            ui.label("KafkaForge").classes("text-lg font-bold tracking-wide")
        ui.button(icon="dark_mode", on_click=dark_mode.toggle).props("flat round dense color=white")

    with drawer:
        ui.label("Menu").classes(
            "text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-3 pt-1"
        )
        for label, route, slug, icon in _MENU_ITEMS:
            active = route == current_route
            item_classes = "flex items-center gap-3 rounded-lg px-3 py-2 w-full no-underline transition-colors "
            item_classes += (
                "bg-primary text-white font-medium"
                if active
                else "text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800"
            )
            with ui.link(target=route).classes(item_classes).mark(f"menu-link-{slug}"):
                ui.icon(icon)
                ui.label(label)

    ui.query(".nicegui-content").classes("w-full max-w-5xl mx-auto p-6 gap-5")
