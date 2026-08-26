import json

from nicegui import events, run, ui

from app.exceptions import ConfigurationNotFoundError, SchemaNotFoundError
from app.services import kafka_service
from app.ui.components import environment_select, layout, schema_form

ROUTE = "/publicar-mensagem"


async def _read_upload_as_text(event: events.UploadEventArguments) -> str:
    return await event.file.text()


@ui.page(ROUTE)
def publicar_mensagem_page() -> None:
    layout.render_menu(ROUTE)

    with ui.row().classes("items-center gap-2"):
        ui.icon("send").classes("text-primary text-3xl")
        ui.label("Publicar Mensagem").classes("text-2xl font-bold")

    # Estado por conexão de cliente (closure da função da página) — o
    # schema selecionado (conteúdo `.avsc` e campos formatados) não tem um
    # campo de formulário próprio, então fica aqui, no mesmo padrão de
    # `configuracoes_kafka.py`/`schemas_avro.py`.
    state: dict[str, object] = {"schema_avsc": None, "schema_fields": None, "payload": {}}

    with ui.column().classes("w-full max-w-3xl gap-4"):
        with ui.card().classes("w-full gap-2"):
            configuration_select = environment_select.render()
            topic_input = (
                ui.input("Tópico").props("outlined dense").classes("w-full").mark("topic-input")
            )
            key_input = (
                ui.input("Chave (opcional)")
                .props("outlined dense")
                .classes("w-full")
                .mark("key-input")
            )

        status_label = ui.label().mark("status-label")

        with ui.card().classes("w-full gap-2"):
            ui.label("Schema (opcional)").classes("text-base font-medium")
            schema_select = (
                ui.select(
                    {nome: nome for nome in kafka_service.list_schema_names()},
                    label="Schema salvo (opcional)",
                )
                .props("outlined dense")
                .classes("w-full")
                .mark("schema-select")
            )
            ui.upload(
                label="Selecionar arquivo .avsc",
                on_upload=lambda event: _handle_schema_upload(event),
                auto_upload=True,
            ).props("outlined").classes("w-full").mark("schema-upload")

            form_container = ui.column().mark("schema-form").classes("w-full gap-1")

        with ui.card().classes("w-full gap-2"):
            ui.label("Payload").classes("text-base font-medium")
            # FR-011: editor de texto no formato JSON — mecanismo mínimo
            # funcional. FR-012: o formulário auto-gerado acima (TASK-030b) é
            # uma alternativa que escreve no mesmo editor — os dois produzem o
            # mesmo payload, e o editor continua disponível e funcional.
            payload_editor = (
                ui.textarea(label="Payload (JSON)")
                .mark("payload-editor")
                .props("rows=10 outlined")
                .classes("w-full font-mono")
            )

            problems_list = ui.column().mark("validation-problems").classes("gap-0 w-full")
            publish_result = ui.column().mark("publish-result").classes("gap-0 w-full")

            with ui.row():
                ui.button("Validar", icon="fact_check", on_click=lambda: _validate()).props(
                    "outline"
                ).mark("validate-button")
                ui.button("Publicar", icon="send", on_click=lambda: _publish()).mark(
                    "publish-button"
                )

        def _on_form_change(payload: dict) -> None:
            payload_editor.value = json.dumps(payload, ensure_ascii=False, indent=2)

        def _rebuild_form() -> None:
            form_container.clear()
            state["payload"] = {}
            if not state["schema_fields"]:
                return
            with form_container:
                schema_form.render(state["schema_fields"], state["payload"], _on_form_change)

        def _set_schema(nome: str, avsc_content: str, fields: list[dict]) -> None:
            state["schema_avsc"] = avsc_content
            state["schema_fields"] = fields
            _rebuild_form()

        def _refresh_schema_options(*, select_nome: str | None = None) -> None:
            nomes = kafka_service.list_schema_names()
            schema_select.options = {nome: nome for nome in nomes}
            if select_nome is not None:
                schema_select.value = select_nome
            schema_select.update()

        def _handle_schema_select(event: events.ValueChangeEventArguments) -> None:
            if not event.value:
                return
            try:
                loaded = kafka_service.get_named_schema(event.value)
            except SchemaNotFoundError as error:
                status_label.text = error.friendly_message
                status_label.classes(replace="text-negative")
                return
            _set_schema(
                loaded.nome,
                loaded.raw_content,
                [{"nome": campo.nome, "tipo": campo.tipo} for campo in loaded.fields],
            )

        schema_select.on_value_change(_handle_schema_select)

        async def _handle_schema_upload(event: events.UploadEventArguments) -> None:
            content = await _read_upload_as_text(event)
            result = kafka_service.save_schema(content)
            if not result.valid:
                status_label.text = result.message
                status_label.classes(replace="text-negative")
                return
            _set_schema(result.nome, result.raw_content, result.fields)
            _refresh_schema_options(select_nome=result.nome)
            ui.notify(f"Schema carregado: {event.file.name}")

        def _current_payload() -> dict:
            return json.loads(payload_editor.value or "{}")

        def _validate() -> None:
            problems_list.clear()
            publish_result.clear()

            if not state["schema_avsc"]:
                status_label.text = "Selecione um arquivo .avsc antes de validar."
                status_label.classes(replace="text-negative")
                return

            try:
                payload = _current_payload()
            except json.JSONDecodeError as error:
                status_label.text = f"O payload não é um JSON válido: {error}"
                status_label.classes(replace="text-negative")
                return

            # FR-013 / cenário 2 de US-003a: services/kafka_service.py é o
            # único caminho de código usado tanto pela UI quanto pela API
            # (messages/validate, TASK-029) para validar um payload —
            # garante que os dois produzem o mesmo resultado (NFR-006).
            result = kafka_service.validate_payload(state["schema_avsc"], payload)

            status_label.text = result.message
            status_label.classes(replace="text-positive" if result.valid else "text-negative")

            if result.problems:
                with problems_list:
                    for problem in result.problems:
                        ui.label(
                            f"{problem['campo']}: esperado '{problem['tipo_esperado']}', "
                            f"recebido '{problem['tipo_recebido']}'"
                        ).classes("text-negative").mark(f"problem-{problem['campo']}")

        async def _publish() -> None:
            problems_list.clear()
            publish_result.clear()

            if not configuration_select.value or not topic_input.value:
                status_label.text = "Selecione uma configuração e informe o tópico antes de publicar."
                status_label.classes(replace="text-negative")
                return

            try:
                payload = _current_payload()
            except json.JSONDecodeError as error:
                status_label.text = f"O payload não é um JSON válido: {error}"
                status_label.classes(replace="text-negative")
                return

            status_label.text = "Publicando..."
            status_label.classes(replace="")

            try:
                # run.io_bound evita bloquear o servidor NiceGUI durante
                # os até 10s do timeout de publicação (decisão Q2).
                result = await run.io_bound(
                    kafka_service.publish,
                    configuration_select.value,
                    topic_input.value,
                    state["schema_avsc"],
                    payload,
                    key_input.value or None,
                )
            except ConfigurationNotFoundError as error:
                status_label.text = error.friendly_message
                status_label.classes(replace="text-negative")
                return

            status_label.text = result.message
            status_label.classes(replace="text-positive" if result.success else "text-negative")

            # SC-004: tópico/partição/offset diretamente na mesma tela.
            if result.success:
                with publish_result:
                    ui.label(f"Tópico: {result.topic}").mark("publish-topic")
                    ui.label(f"Partição: {result.partition}").mark("publish-partition")
                    ui.label(f"Offset: {result.offset}").mark("publish-offset")
