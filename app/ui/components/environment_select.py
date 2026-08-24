from nicegui import ui

from app.services import kafka_service


def render(*, label: str = "Configuração") -> ui.select:
    """Seletor de Configuração de Ambiente reutilizável (US-006, TASK-052)
    — usado pela tela Publicar Mensagem; evita duplicar a lógica de listar
    configurações salvas em cada tela que precisa escolher uma."""
    configuracoes = {c.nome: c.nome for c in kafka_service.list_configurations()}
    return ui.select(configuracoes, label=label).mark("configuration-select").classes("w-full")
