from nicegui import events, run, ui

from app.config.models import SchemaRegistryConfig
from app.exceptions import ConfigurationNotFoundError
from app.services import kafka_service
from app.ui.components import environment_select, layout

ROUTE = "/configuracoes/schema-registry"


async def _read_upload_as_text(event: events.UploadEventArguments) -> str:
    return await event.file.text()


@ui.page(ROUTE)
def configuracoes_schema_registry_page() -> None:
    """Configura o bloco `schema_registry` de uma Configuração de Ambiente
    já existente, de forma independente do bloco `kafka` (US-005a, FR-005)
    — a Configuração de Ambiente em si continua sendo criada em
    Configurações → Kafka (TASK-014); esta tela só edita/testa o Schema
    Registry de uma configuração já cadastrada."""
    layout.render_menu(ROUTE)

    with ui.row().classes("items-center gap-2"):
        ui.icon("schema").classes("text-primary text-3xl")
        ui.label("Configurações — Schema Registry").classes("text-2xl font-bold")

    state: dict[str, str | None] = {"ca_cert": None, "client_cert": None, "client_key": None}

    with ui.column().classes("w-full max-w-2xl gap-3"):
        with ui.card().classes("w-full gap-2"):
            config_select = environment_select.render(label="Configuração de ambiente")

            url_input = (
                ui.input("URL")
                .props('outlined dense placeholder="http://localhost:8081"')
                .classes("w-full")
                .mark("url-input")
            )
            username_input = (
                ui.input("Usuário").props("outlined dense").classes("w-full").mark("username-input")
            )
            password_input = (
                ui.input("Senha", password=True)
                .props("outlined dense")
                .classes("w-full")
                .mark("password-input")
            )

            def _make_upload_handler(field: str, rotulo: str):
                async def handler(event: events.UploadEventArguments) -> None:
                    state[field] = await _read_upload_as_text(event)
                    ui.notify(f"{rotulo} carregado: {event.file.name}")

                return handler

            ui.upload(
                label="Certificado da autoridade (CA)",
                on_upload=_make_upload_handler("ca_cert", "Certificado CA"),
                auto_upload=True,
            ).props("outlined").classes("w-full").mark("ca-cert-upload")
            ui.upload(
                label="Certificado do cliente",
                on_upload=_make_upload_handler("client_cert", "Certificado do cliente"),
                auto_upload=True,
            ).props("outlined").classes("w-full").mark("client-cert-upload")
            ui.upload(
                label="Chave privada do cliente",
                on_upload=_make_upload_handler("client_key", "Chave privada do cliente"),
                auto_upload=True,
            ).props("outlined").classes("w-full").mark("client-key-upload")

        status_label = ui.label().mark("status-label")

        def _clear_form() -> None:
            state["ca_cert"] = None
            state["client_cert"] = None
            state["client_key"] = None
            url_input.value = ""
            username_input.value = ""
            password_input.value = ""

        def _handle_config_select(event: events.ValueChangeEventArguments) -> None:
            _clear_form()
            status_label.text = ""
            if not event.value:
                return
            try:
                configuration = kafka_service.get_configuration(event.value)
            except ConfigurationNotFoundError as error:
                status_label.text = error.friendly_message
                status_label.classes(replace="text-negative")
                return

            schema_registry = configuration.schema_registry
            if schema_registry is None:
                return
            state["ca_cert"] = schema_registry.ca_cert
            state["client_cert"] = schema_registry.client_cert
            state["client_key"] = schema_registry.client_key
            url_input.value = schema_registry.url
            username_input.value = schema_registry.username or ""
            password_input.value = schema_registry.password or ""

        config_select.on_value_change(_handle_config_select)

        def _schema_registry_from_form() -> SchemaRegistryConfig:
            return SchemaRegistryConfig(
                url=url_input.value,
                username=username_input.value or None,
                password=password_input.value or None,
                ca_cert=state["ca_cert"],
                client_cert=state["client_cert"],
                client_key=state["client_key"],
            )

        def _save() -> None:
            nome = config_select.value
            if not nome:
                status_label.text = "Selecione uma configuração de ambiente."
                status_label.classes(replace="text-negative")
                return
            if not url_input.value:
                status_label.text = "Informe a URL do Schema Registry."
                status_label.classes(replace="text-negative")
                return

            try:
                configuration = kafka_service.get_configuration(nome)
            except ConfigurationNotFoundError as error:
                status_label.text = error.friendly_message
                status_label.classes(replace="text-negative")
                return

            updated = configuration.model_copy(update={"schema_registry": _schema_registry_from_form()})
            kafka_service.update_configuration(nome, updated)

            status_label.text = f"Schema Registry de '{nome}' salvo com sucesso."
            status_label.classes(replace="text-positive")

        async def _test() -> None:
            # Testa o que está no formulário agora, não a última configuração
            # salva (achado: "Testar" bloqueado sem clicar em Salvar antes) —
            # não exige Salvar primeiro.
            nome = config_select.value
            if not nome:
                status_label.text = "Selecione uma configuração de ambiente."
                status_label.classes(replace="text-negative")
                return
            if not url_input.value:
                status_label.text = "Informe a URL do Schema Registry."
                status_label.classes(replace="text-negative")
                return

            status_label.text = "Testando Schema Registry..."
            status_label.classes(replace="")
            # run.io_bound evita bloquear o servidor NiceGUI durante os até
            # 10s do timeout de teste (decisão Q2).
            result = await run.io_bound(
                kafka_service.test_schema_registry_config, nome, _schema_registry_from_form()
            )

            status_label.text = result.message
            status_label.classes(replace="text-positive" if result.success else "text-negative")

        with ui.row():
            ui.button("Salvar", icon="save", on_click=_save).mark("save-button")
            ui.button(
                "Testar Schema Registry", icon="wifi_tethering", on_click=_test
            ).props("outline").mark("test-schema-registry-button")
