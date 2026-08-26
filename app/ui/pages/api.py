from nicegui import ui

from app.ui.components import layout

ROUTE = "/api"


@ui.page(ROUTE)
def api_page() -> None:
    """US-004b: acesso à documentação interativa do serviço local a partir
    da navegação principal da UI — `/docs` já é gerado automaticamente
    pelo FastAPI (TASK-040/TASK-041), sem trabalho de documentação manual
    aqui."""
    layout.render_menu(ROUTE)

    with ui.row().classes("items-center gap-2"):
        ui.icon("api").classes("text-primary text-3xl")
        ui.label("API").classes("text-2xl font-bold")

    with ui.card().classes("w-full gap-3"):
        ui.label(
            "O serviço local do KafkaForge expõe a mesma capacidade de "
            "publicação da tela por HTTP, para uso em automações."
        ).classes("text-slate-600 dark:text-slate-300")
        ui.link(
            "Abrir documentação interativa (/docs)", "/docs", new_tab=True
        ).classes("text-primary font-medium").mark("docs-link")

    with ui.card().classes("w-full p-0 overflow-hidden"):
        ui.html(
            '<iframe src="/docs" style="width:100%;height:80vh;border:none;"></iframe>'
        ).classes("w-full").mark("docs-iframe")
