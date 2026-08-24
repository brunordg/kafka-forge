from pydantic import ValidationError

from nicegui import events, run, ui

from app.config.models import (
    EnvironmentConfiguration,
    KafkaConfig,
    SaslMechanism,
    SchemaRegistryConfig,
    SecurityProtocol,
)
from app.exceptions import ConfigurationAlreadyExistsError, ConfigurationNotFoundError
from app.services import kafka_service
from app.ui.components import layout

ROUTE = "/configuracoes/kafka"

_SECURITY_PROTOCOL_OPTIONS = {protocol.value: protocol.value for protocol in SecurityProtocol}
_SASL_MECHANISM_OPTIONS = {"": "(nenhum)", **{mechanism.value: mechanism.value for mechanism in SaslMechanism}}


async def _read_upload_as_text(event: events.UploadEventArguments) -> str:
    return await event.file.text()


@ui.page(ROUTE)
def configuracoes_kafka_page() -> None:
    layout.render_menu()

    # Estado por conexão de cliente (closure da função da página, não uma
    # variável de módulo) — cada aba/navegador que abre esta página tem o
    # seu próprio estado de edição, sem interferir com o de outra pessoa.
    state: dict[str, str | None] = {
        "editing_nome": None,
        "ca_cert": None,
        "client_cert": None,
        "client_key": None,
    }
    existing_schema_registry: dict[str, SchemaRegistryConfig | None] = {"value": None}

    ui.label("Configurações — Kafka").classes("text-2xl font-bold")

    with ui.row().classes("w-full items-start gap-8"):
        with ui.column().classes("w-96 gap-2"):
            form_title = ui.label("Nova configuração").classes("text-lg")

            nome_input = ui.input("Nome da configuração").mark("nome-input").classes("w-full")
            bootstrap_servers_input = (
                ui.input("Endereço dos brokers (bootstrap_servers)")
                .mark("bootstrap-servers-input")
                .classes("w-full")
            )
            security_protocol_select = (
                ui.select(
                    _SECURITY_PROTOCOL_OPTIONS,
                    label="Protocolo de segurança",
                    value=SecurityProtocol.PLAINTEXT.value,
                )
                .mark("security-protocol-select")
                .classes("w-full")
            )
            sasl_mechanism_select = (
                ui.select(_SASL_MECHANISM_OPTIONS, label="Mecanismo SASL", value="")
                .mark("sasl-mechanism-select")
                .classes("w-full")
            )
            username_input = ui.input("Usuário").mark("username-input").classes("w-full")
            password_input = (
                ui.input("Senha", password=True).mark("password-input").classes("w-full")
            )
            client_key_password_input = (
                ui.input("Senha da chave privada", password=True)
                .mark("client-key-password-input")
                .classes("w-full")
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
            ).mark("ca-cert-upload").classes("w-full")
            ui.upload(
                label="Certificado do cliente",
                on_upload=_make_upload_handler("client_cert", "Certificado do cliente"),
                auto_upload=True,
            ).mark("client-cert-upload").classes("w-full")
            ui.upload(
                label="Chave privada do cliente",
                on_upload=_make_upload_handler("client_key", "Chave privada do cliente"),
                auto_upload=True,
            ).mark("client-key-upload").classes("w-full")

            status_label = ui.label().mark("status-label")

            def _clear_form() -> None:
                state["editing_nome"] = None
                state["ca_cert"] = None
                state["client_cert"] = None
                state["client_key"] = None
                existing_schema_registry["value"] = None
                form_title.text = "Nova configuração"
                nome_input.value = ""
                bootstrap_servers_input.value = ""
                security_protocol_select.value = SecurityProtocol.PLAINTEXT.value
                sasl_mechanism_select.value = ""
                username_input.value = ""
                password_input.value = ""
                client_key_password_input.value = ""
                status_label.text = ""

            def _save() -> None:
                try:
                    kafka = KafkaConfig(
                        bootstrap_servers=bootstrap_servers_input.value,
                        security_protocol=SecurityProtocol(security_protocol_select.value),
                        sasl_mechanism=(
                            SaslMechanism(sasl_mechanism_select.value)
                            if sasl_mechanism_select.value
                            else None
                        ),
                        username=username_input.value or None,
                        password=password_input.value or None,
                        ca_cert=state["ca_cert"],
                        client_cert=state["client_cert"],
                        client_key=state["client_key"],
                        client_key_password=client_key_password_input.value or None,
                    )
                    configuration = EnvironmentConfiguration(
                        nome=nome_input.value,
                        kafka=kafka,
                        schema_registry=existing_schema_registry["value"],
                    )

                    if state["editing_nome"] is None:
                        saved = kafka_service.create_configuration(configuration)
                    else:
                        saved = kafka_service.update_configuration(
                            state["editing_nome"], configuration
                        )

                    state["editing_nome"] = saved.nome
                    form_title.text = f"Editando: {saved.nome}"
                    status_label.text = f"Configuração '{saved.nome}' salva com sucesso."
                    status_label.classes(replace="text-positive")
                    _refresh_list()
                except ValidationError as error:
                    mensagens = "; ".join(item["msg"] for item in error.errors())
                    status_label.text = f"Dados inválidos: {mensagens}"
                    status_label.classes(replace="text-negative")
                except (ConfigurationAlreadyExistsError, ConfigurationNotFoundError) as error:
                    status_label.text = error.friendly_message
                    status_label.classes(replace="text-negative")

            with ui.row():
                ui.button("Salvar", on_click=_save).mark("save-button")
                ui.button("Nova configuração", on_click=_clear_form).mark("clear-button")

        with ui.column().classes("flex-1 gap-2"):
            ui.label("Configurações salvas").classes("text-lg")
            saved_list = ui.column().mark("saved-configurations-list").classes("w-full gap-1")

            def _load_into_form(configuration: EnvironmentConfiguration) -> None:
                state["editing_nome"] = configuration.nome
                state["ca_cert"] = configuration.kafka.ca_cert
                state["client_cert"] = configuration.kafka.client_cert
                state["client_key"] = configuration.kafka.client_key
                existing_schema_registry["value"] = configuration.schema_registry

                form_title.text = f"Editando: {configuration.nome}"
                nome_input.value = configuration.nome
                bootstrap_servers_input.value = configuration.kafka.bootstrap_servers
                security_protocol_select.value = configuration.kafka.security_protocol.value
                sasl_mechanism_select.value = (
                    configuration.kafka.sasl_mechanism.value
                    if configuration.kafka.sasl_mechanism
                    else ""
                )
                username_input.value = configuration.kafka.username or ""
                password_input.value = configuration.kafka.password or ""
                client_key_password_input.value = configuration.kafka.client_key_password or ""
                status_label.text = ""

            delete_pending: dict[str, str | None] = {"nome": None}

            with ui.dialog() as delete_dialog, ui.card():
                ui.label().bind_text_from(
                    delete_pending, "nome", lambda nome: f"Remover a configuração '{nome}'?"
                )
                with ui.row():
                    ui.button(
                        "Cancelar", on_click=delete_dialog.close
                    ).mark("cancel-delete-button")

                    def _confirm_delete() -> None:
                        nome = delete_pending["nome"]
                        delete_dialog.close()
                        if nome is None:
                            return
                        try:
                            kafka_service.delete_configuration(nome)
                            if state["editing_nome"] == nome:
                                _clear_form()
                            status_label.text = f"Configuração '{nome}' removida com sucesso."
                            status_label.classes(replace="text-positive")
                            _refresh_list()
                        except ConfigurationNotFoundError as error:
                            status_label.text = error.friendly_message
                            status_label.classes(replace="text-negative")
                            _refresh_list()

                    ui.button("Remover", on_click=_confirm_delete).mark("confirm-delete-button")

            def _ask_delete_confirmation(nome: str) -> None:
                delete_pending["nome"] = nome
                delete_dialog.open()

            def _make_test_connection_handler(nome: str):
                async def handler() -> None:
                    status_label.text = f"Testando conexão com '{nome}'..."
                    status_label.classes(replace="")
                    try:
                        # `run.io_bound` evita bloquear o servidor NiceGUI
                        # durante os até 10s do timeout de conexão (decisão
                        # Q2) enquanto o teste está em andamento.
                        result = await run.io_bound(kafka_service.test_connection, nome)
                    except ConfigurationNotFoundError as error:
                        status_label.text = error.friendly_message
                        status_label.classes(replace="text-negative")
                        return

                    status_label.text = result.message
                    status_label.classes(
                        replace="text-positive" if result.success else "text-negative"
                    )

                return handler

            def _refresh_list() -> None:
                saved_list.clear()
                configurations = kafka_service.list_configurations()
                with saved_list:
                    if not configurations:
                        ui.label("Nenhuma configuração salva ainda.").classes("text-grey")
                    for configuration in configurations:
                        with ui.row().classes("items-center gap-2").mark(
                            f"saved-configuration-{configuration.nome}"
                        ):
                            ui.label(
                                f"{configuration.nome} — {configuration.kafka.bootstrap_servers}"
                            )
                            ui.button(
                                "Editar",
                                on_click=lambda c=configuration: _load_into_form(c),
                            ).mark(f"edit-button-{configuration.nome}")
                            ui.button(
                                "Testar conexão",
                                on_click=_make_test_connection_handler(configuration.nome),
                            ).mark(f"test-connection-button-{configuration.nome}")
                            ui.button(
                                "Remover",
                                on_click=lambda c=configuration: _ask_delete_confirmation(c.nome),
                            ).mark(f"delete-button-{configuration.nome}")

    _refresh_list()
