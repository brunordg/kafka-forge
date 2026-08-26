from nicegui import events, ui

from app.exceptions import SchemaRegistryError
from app.services import kafka_service
from app.ui.components import avro_type, environment_select, layout

ROUTE = "/schemas/avro"


async def _read_upload_as_text(event: events.UploadEventArguments) -> str:
    return await event.file.text()


@ui.page(ROUTE)
def schemas_avro_page() -> None:
    layout.render_menu(ROUTE)

    with ui.row().classes("items-center gap-2"):
        ui.icon("description").classes("text-primary text-3xl")
        ui.label("Schemas Avro").classes("text-2xl font-bold")

    status_label = ui.label().mark("status-label")

    with ui.card().classes("w-full gap-3"):
        ui.upload(
            label="Selecionar arquivo .avsc",
            on_upload=lambda event: _handle_upload(event),
            auto_upload=True,
        ).props("outlined").classes("w-full").mark("avsc-upload")

        ui.separator()

        # US-005b/FR-019 (TASK-050): alternativa ao upload — selecionar um
        # schema já registrado no Schema Registry de uma Configuração de
        # Ambiente, em vez de subir um novo arquivo `.avsc`.
        ui.label("Selecionar do Schema Registry").classes("text-base font-medium")
        with ui.row().classes("items-end gap-2"):
            registry_config_select = environment_select.render(label="Configuração de ambiente")
            subject_select = (
                ui.select({}, label="Subject")
                .props("outlined dense")
                .classes("w-48")
                .mark("subject-select")
            )
            ui.button(
                "Usar este schema", icon="check", on_click=lambda: _use_registry_schema()
            ).props("outline").mark("use-registry-schema-button")

    with ui.card().classes("w-full gap-2") as details:
        ui.label("Detalhes do schema").classes("text-base font-medium")
        nome_label = ui.label().classes("text-lg font-semibold").mark("schema-nome")
        namespace_label = ui.label().classes("text-slate-500").mark("schema-namespace")
        ui.label("Campos").classes(
            "text-sm font-semibold uppercase tracking-wide text-slate-400 mt-2"
        )
        fields_list = ui.column().mark("schema-fields").classes("gap-1")
        ui.label("Conteúdo original").classes(
            "text-sm font-semibold uppercase tracking-wide text-slate-400 mt-2"
        )
        raw_content_area = (
            ui.textarea()
            .mark("schema-raw-content")
            .props("readonly outlined")
            .classes("w-full font-mono")
        )
    details.visible = False

    ui.label("Schemas carregados").classes("text-lg font-medium")
    with ui.card().classes("w-full"):
        saved_schemas_list = ui.row().mark("saved-schemas-list").classes("gap-2 flex-wrap")

    def _refresh_saved_schemas() -> None:
        saved_schemas_list.clear()
        nomes = kafka_service.list_schema_names()
        with saved_schemas_list:
            if not nomes:
                ui.label("Nenhum schema carregado ainda.").classes("text-grey")
            for nome in nomes:
                ui.badge(nome, color="secondary").mark(f"saved-schema-{nome}")

    def _show_schema_result(result: kafka_service.SchemaValidationResult) -> None:
        if not result.valid:
            status_label.text = result.message
            status_label.classes(replace="text-negative")
            details.visible = False
            return

        status_label.text = f"Schema '{result.nome}' válido."
        status_label.classes(replace="text-positive")

        nome_label.text = f"Nome: {result.nome}"
        namespace_label.text = f"Namespace: {result.namespace or '(nenhum)'}"

        fields_list.clear()
        with fields_list:
            for campo in result.fields or []:
                # A string de `campo["tipo"]` já vem pronta de
                # `avro/schema_loader.py` (US-002b); o componente
                # `ui/components/avro_type.py` é o único lugar que decide
                # como exibi-la, reutilizado por qualquer tela futura que
                # precise mostrar campos de um schema.
                with ui.row().classes("items-center gap-1"):
                    ui.label(f"{campo['nome']}:")
                    avro_type.render(campo["tipo"])

        raw_content_area.value = result.raw_content or ""
        details.visible = True
        _refresh_saved_schemas()

    async def _handle_upload(event: events.UploadEventArguments) -> None:
        # cenário 1/2 do Acceptance Scenario de US-002a: um schema válido
        # exibe nome/namespace/campos/conteúdo original; um inválido exibe
        # só a explicação compreensível, sem interromper o restante da
        # tela (FR-009) — o upload continua disponível para uma nova
        # tentativa.
        content = await _read_upload_as_text(event)
        # `save_schema`, não `validate_schema`: nesta tela, fazer upload é
        # "carregar" o schema na ferramenta — ele passa a ficar disponível
        # por nome em Publicar Mensagem e na API (`POST /api/v1/messages`,
        # TASK-034b). `validate_schema` continua reservada à inspeção pura
        # de `POST /api/v1/schema/validate` (TASK-022), sem persistir.
        _show_schema_result(kafka_service.save_schema(content))

    def _refresh_subjects() -> None:
        nome = registry_config_select.value
        subject_select.options = {}
        subject_select.value = None
        if not nome:
            subject_select.update()
            return
        try:
            subjects = kafka_service.list_schema_registry_subjects(nome)
        except SchemaRegistryError as error:
            status_label.text = error.friendly_message
            status_label.classes(replace="text-negative")
            subject_select.update()
            return
        subject_select.options = {subject: subject for subject in subjects}
        subject_select.update()

    registry_config_select.on_value_change(lambda _event: _refresh_subjects())

    def _use_registry_schema() -> None:
        nome = registry_config_select.value
        subject = subject_select.value
        if not nome or not subject:
            status_label.text = "Selecione uma configuração e um subject."
            status_label.classes(replace="text-negative")
            return
        try:
            result = kafka_service.load_schema_from_registry(nome, subject)
        except SchemaRegistryError as error:
            status_label.text = error.friendly_message
            status_label.classes(replace="text-negative")
            return
        _show_schema_result(result)

    _refresh_saved_schemas()
