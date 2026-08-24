from nicegui import ui

from app.ui.components import layout

ROUTE = "/api"


@ui.page(ROUTE)
def api_page() -> None:
    """US-004b: acesso à documentação interativa do serviço local a partir
    da navegação principal da UI — `/docs` já é gerado automaticamente
    pelo FastAPI (TASK-040/TASK-041), sem trabalho de documentação manual
    aqui."""
    layout.render_menu()

    ui.label("API").classes("text-2xl font-bold")
    ui.label(
        "O serviço local do KafkaForge expõe a mesma capacidade de "
        "publicação da tela por HTTP, para uso em automações."
    )
    ui.link("Abrir documentação interativa (/docs)", "/docs", new_tab=True).mark("docs-link")
    ui.html(
        '<iframe src="/docs" style="width:100%;height:80vh;border:1px solid #ccc;"></iframe>'
    ).mark("docs-iframe")
