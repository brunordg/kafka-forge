import time
from dataclasses import dataclass, field

from confluent_kafka import KafkaException

from app.avro import schema_loader
from app.avro import schema_store
from app.avro import validator as avro_validator
from app.config import manager as config_manager
from app.config.models import EnvironmentConfiguration, SchemaRegistryConfig
from app.exceptions import (
    AvroSchemaError,
    KafkaAuthenticationError,
    MessagePublishError,
    MessageSerializationError,
    SchemaRegistryError,
)
from app.kafka import connection as kafka_connection
from app.kafka import producer as kafka_producer
from app.kafka import serializer as kafka_serializer
from app.registry import client as registry_client
from app.services import operation_log


@dataclass
class ConnectionTestResult:
    success: bool
    message: str
    technical_detail: str = ""


@dataclass
class ConfigurationTestResult:
    kafka: ConnectionTestResult
    schema_registry: ConnectionTestResult | None = None


@dataclass
class SchemaValidationResult:
    valid: bool
    message: str
    nome: str | None = None
    namespace: str | None = None
    fields: list | None = None
    raw_content: str | None = None


@dataclass
class PayloadValidationResult:
    valid: bool
    message: str
    problems: list = field(default_factory=list)


@dataclass
class PublishResult:
    success: bool
    message: str
    topic: str | None = None
    partition: int | None = None
    offset: int | None = None


@dataclass
class DashboardStatus:
    active_configuration: str | None
    kafka_connected: bool | None
    schema_registry_connected: bool | None
    schemas_loaded: int
    last_publish_topic: str | None = None
    last_publish_partition: int | None = None
    last_publish_offset: int | None = None


def _get_configuration_snapshot(nome_configuracao: str) -> EnvironmentConfiguration:
    """Lê a Configuração de Ambiente do armazenamento local a cada chamada
    — nunca uma referência cacheada/compartilhada entre chamadas
    concorrentes de UI e API (edge case de concorrência, seção 11 do
    plano)."""
    return config_manager.get_configuration(nome_configuracao)


def list_configurations() -> list[EnvironmentConfiguration]:
    """Lista as Configurações de Ambiente salvas (US-001a, US-006). `ui/`
    e `api/` só chegam a `config/manager.py` (TASK-008) através deste
    módulo, nunca diretamente."""
    return config_manager.list_configurations()


def get_configuration(nome: str) -> EnvironmentConfiguration:
    """Usado pela tela Configurações → Schema Registry (TASK-047) para
    carregar os dados atuais de uma Configuração de Ambiente antes de
    editar só o bloco `schema_registry`, preservando o bloco `kafka`."""
    return config_manager.get_configuration(nome)


def create_configuration(configuration: EnvironmentConfiguration) -> EnvironmentConfiguration:
    """Cria uma nova Configuração de Ambiente (US-001a, cenário 1).
    Propaga `ConfigurationAlreadyExistsError` de `config/manager.py`
    quando o nome já existe, sem sobrescrever silenciosamente."""
    return config_manager.create_configuration(configuration)


def update_configuration(
    nome_atual: str, configuration: EnvironmentConfiguration
) -> EnvironmentConfiguration:
    """Atualiza uma Configuração de Ambiente já existente (formulário de
    edição da TASK-014). Propaga `ConfigurationNotFoundError` quando
    `nome_atual` não existe."""
    return config_manager.update_configuration(nome_atual, configuration)


def delete_configuration(nome: str) -> None:
    """Remove uma Configuração de Ambiente salva (US-001a, fecha a lacuna
    de FR-001 identificada em `analysis.md`, achado G1). Propaga
    `ConfigurationNotFoundError` de `config/manager.py` quando `nome` não
    existe, sem afetar as demais configurações salvas."""
    config_manager.delete_configuration(nome)


# Prefixos de mensagem amigável por nome de erro `librdkafka` (cenário 2 de
# US-001b: broker inexistente, credencial inválida, certificado incorreto).
# Um código sem entrada aqui ainda produz uma falha compreensível — apenas
# com um prefixo genérico — em vez de deixar de tratar o erro.
_KAFKA_ERROR_FRIENDLY_PREFIXES: dict[str, str] = {
    "_TRANSPORT": "Não foi possível conectar aos brokers informados",
    "_RESOLVE": "Não foi possível resolver o endereço dos brokers informados",
    "_TIMED_OUT": "Tempo esgotado ao tentar conectar aos brokers informados",
    "_AUTHENTICATION": "Falha de autenticação ao conectar ao Kafka",
    "SASL_AUTHENTICATION_FAILED": "Falha de autenticação SASL ao conectar ao Kafka",
    "_SSL": "Falha ao validar o certificado SSL/TLS informado",
    "TOPIC_AUTHORIZATION_FAILED": "Sem autorização para acessar o tópico informado",
    "GROUP_AUTHORIZATION_FAILED": "Sem autorização para acessar o cluster Kafka informado",
    "CLUSTER_AUTHORIZATION_FAILED": "Sem autorização para acessar o cluster Kafka informado",
}


def _describe_kafka_error(kafka_error) -> tuple[str, str]:
    technical_detail = kafka_error.str()
    prefix = _KAFKA_ERROR_FRIENDLY_PREFIXES.get(kafka_error.name(), "Falha ao conectar ao Kafka")
    return f"{prefix}: {technical_detail}", technical_detail


def _record_connection_test(
    nome_configuracao: str,
    started_at: float,
    *,
    success: bool,
    message: str,
    technical_detail: str = "",
    tipo_operacao: operation_log.OperationType = operation_log.OperationType.TESTE_CONEXAO,
) -> ConnectionTestResult:
    duracao_ms = int((time.monotonic() - started_at) * 1000)
    operation_log.append_operation_record(
        tipo_operacao,
        operation_log.OperationResult.SUCESSO if success else operation_log.OperationResult.ERRO,
        duracao_ms,
        configuracao=nome_configuracao,
        erro_tecnico=None if success else technical_detail,
    )
    return ConnectionTestResult(success=success, message=message, technical_detail=technical_detail)


def test_connection(nome_configuracao: str) -> ConnectionTestResult:
    """Testa a conectividade Kafka da configuração indicada, sem publicar
    nada (US-001b, NFR-002). Usa `AdminClient.list_topics` — uma chamada de
    apenas leitura de metadados — para nunca correr o risco de publicar
    mensagens nem registrar/alterar schemas."""
    configuration = _get_configuration_snapshot(nome_configuracao)

    started_at = time.monotonic()
    try:
        admin_client = kafka_connection.build_admin_client(configuration)
        admin_client.list_topics(timeout=kafka_connection.CONNECTION_TIMEOUT_MS / 1000)
    except KafkaAuthenticationError as error:
        return _record_connection_test(
            nome_configuracao,
            started_at,
            success=False,
            message=error.friendly_message,
            technical_detail=error.technical_detail,
        )
    except KafkaException as error:
        message, technical_detail = _describe_kafka_error(error.args[0])
        return _record_connection_test(
            nome_configuracao,
            started_at,
            success=False,
            message=message,
            technical_detail=technical_detail,
        )

    return _record_connection_test(
        nome_configuracao,
        started_at,
        success=True,
        message="Conexão com o Kafka estabelecida com sucesso.",
    )


def test_schema_registry(nome_configuracao: str) -> ConnectionTestResult:
    """Testa a acessibilidade do Schema Registry da configuração indicada,
    sem registrar nada (US-005a, NFR-002), sobre `registry/client.py`
    (TASK-045). Quando o ambiente não tem Schema Registry configurado
    (FR-007), retorna falha com uma mensagem que deixa isso explícito, em
    vez de tentar testar algo que não existe."""
    configuration = _get_configuration_snapshot(nome_configuracao)
    started_at = time.monotonic()

    if configuration.schema_registry is None:
        return _record_connection_test(
            nome_configuracao,
            started_at,
            success=False,
            message="Nenhum Schema Registry configurado para este ambiente.",
            tipo_operacao=operation_log.OperationType.TESTE_SCHEMA_REGISTRY,
        )

    try:
        registry_client.test_connection(configuration.schema_registry)
    except SchemaRegistryError as error:
        return _record_connection_test(
            nome_configuracao,
            started_at,
            success=False,
            message=error.friendly_message,
            technical_detail=error.technical_detail,
            tipo_operacao=operation_log.OperationType.TESTE_SCHEMA_REGISTRY,
        )

    return _record_connection_test(
        nome_configuracao,
        started_at,
        success=True,
        message="Schema Registry acessível.",
        tipo_operacao=operation_log.OperationType.TESTE_SCHEMA_REGISTRY,
    )


def test_configuration(nome_configuracao: str) -> ConfigurationTestResult:
    """Orquestra o teste de uma Configuração de Ambiente completa (US-001b +
    US-005a): sempre testa o Kafka; testa o Schema Registry apenas quando
    ele está configurado para o ambiente (TASK-046) — os dois resultados
    ficam separados e identificáveis, em vez de um único booleano
    combinado."""
    configuration = _get_configuration_snapshot(nome_configuracao)
    kafka_result = test_connection(nome_configuracao)
    schema_registry_result = (
        test_schema_registry(nome_configuracao) if configuration.schema_registry is not None else None
    )
    return ConfigurationTestResult(kafka=kafka_result, schema_registry=schema_registry_result)


def _require_schema_registry(configuration: EnvironmentConfiguration) -> SchemaRegistryConfig:
    if configuration.schema_registry is None:
        raise SchemaRegistryError("Nenhum Schema Registry configurado para este ambiente.")
    return configuration.schema_registry


def list_schema_registry_subjects(nome_configuracao: str) -> list[str]:
    """US-005b, cenário 1: lista os subjects existentes no Schema Registry
    da configuração indicada, sobre `registry/client.py` (TASK-048)."""
    configuration = _get_configuration_snapshot(nome_configuracao)
    return registry_client.list_subjects(_require_schema_registry(configuration))


def list_schema_registry_versions(nome_configuracao: str, subject: str) -> list[int]:
    configuration = _get_configuration_snapshot(nome_configuracao)
    return registry_client.list_versions(_require_schema_registry(configuration), subject)


def load_schema_from_registry(
    nome_configuracao: str, subject: str, version: int | str = "latest"
) -> SchemaValidationResult:
    """Seleciona um schema já registrado no Schema Registry como
    alternativa ao upload de um `.avsc` (US-005b, FR-019, TASK-050) — o
    conteúdo obtido é persistido localmente por nome exatamente como um
    upload (`save_schema`), ficando utilizável nos mesmos fluxos de
    validação e publicação."""
    configuration = _get_configuration_snapshot(nome_configuracao)
    avsc_content = registry_client.get_schema(_require_schema_registry(configuration), subject, version)
    return save_schema(avsc_content)


def _record_schema_validation(
    started_at: float, *, valid: bool, message: str, schema_nome: str | None = None
) -> None:
    # TASK-055/FR-024: validate_schema e save_schema também geram
    # exatamente um Registro de Operação por chamada, como test_connection
    # e validate_payload — sem isso, uma validação de schema mal-sucedida
    # não deixaria rastro nenhum no histórico (SC-007).
    duracao_ms = int((time.monotonic() - started_at) * 1000)
    operation_log.append_operation_record(
        operation_log.OperationType.VALIDACAO_SCHEMA,
        operation_log.OperationResult.SUCESSO if valid else operation_log.OperationResult.ERRO,
        duracao_ms,
        schema=schema_nome,
        erro_tecnico=None if valid else message,
    )


def validate_schema(avsc_content: str) -> SchemaValidationResult:
    """Analisa e valida a estrutura de um arquivo `.avsc` (US-002a/US-002b),
    sobre `avro/schema_loader.py` (TASK-021). Nunca propaga
    `AvroSchemaError` — um schema inválido vira um resultado com
    `valid=False` e uma mensagem compreensível, nunca uma exceção não
    tratada (FR-009). A formatação recursiva amigável de tipos compostos
    (union/array/map/enum/record aninhado) é escopo de US-002b (TASK-024),
    sobre o mesmo `avro/schema_loader.py`."""
    started_at = time.monotonic()
    try:
        loaded_schema = schema_loader.load_schema(avsc_content)
    except AvroSchemaError as error:
        _record_schema_validation(started_at, valid=False, message=error.friendly_message)
        return SchemaValidationResult(valid=False, message=error.friendly_message)

    _record_schema_validation(started_at, valid=True, message="", schema_nome=loaded_schema.nome)
    return _to_schema_validation_result(loaded_schema)


def _to_schema_validation_result(loaded_schema: schema_loader.LoadedAvroSchema) -> SchemaValidationResult:
    return SchemaValidationResult(
        valid=True,
        message="Schema Avro válido.",
        nome=loaded_schema.nome,
        namespace=loaded_schema.namespace,
        fields=[{"nome": campo.nome, "tipo": campo.tipo} for campo in loaded_schema.fields],
        raw_content=loaded_schema.raw_content,
    )


def save_schema(avsc_content: str) -> SchemaValidationResult:
    """Valida e persiste um schema Avro sob o nome declarado no próprio
    `.avsc` (TASK-034b, gap identificado ao implementar TASK-037/TASK-038:
    o contrato `POST /api/v1/messages` do briefing referencia um schema por
    nome — `"schema": "Pedido"` —, o que exige um schema previamente
    carregado e reutilizável por nome, não apenas validado uma vez).
    Diferente de `validate_schema` (TASK-022, usada por `POST /api/v1/
    schema/validate`, que é uma operação de inspeção pura, sem persistir
    nada), esta função é usada pela tela Schemas Avro (upload = carregar o
    schema na ferramenta) e por qualquer fluxo que precise tornar um schema
    selecionável depois. Também gera um Registro de Operação (TASK-055),
    igual a `validate_schema`."""
    started_at = time.monotonic()
    try:
        loaded_schema = schema_loader.load_schema(avsc_content)
    except AvroSchemaError as error:
        _record_schema_validation(started_at, valid=False, message=error.friendly_message)
        return SchemaValidationResult(valid=False, message=error.friendly_message)

    schema_store.save_schema(loaded_schema)
    _record_schema_validation(started_at, valid=True, message="", schema_nome=loaded_schema.nome)
    return _to_schema_validation_result(loaded_schema)


def list_schema_names() -> list[str]:
    return [loaded_schema.nome for loaded_schema in schema_store.list_schemas()]


def count_schemas() -> int:
    return schema_store.count_schemas()


def get_named_schema(nome: str) -> schema_loader.LoadedAvroSchema:
    """Recupera um schema previamente salvo por nome. Propaga
    `SchemaNotFoundError` de `avro/schema_store.py` quando o nome não
    existe — usada por `POST /api/v1/messages` (cenário 3 de US-004a:
    schema inexistente informado por uma automação)."""
    return schema_store.get_schema(nome)


def _record_payload_validation(
    started_at: float,
    *,
    valid: bool,
    message: str,
    problems: list[dict],
    schema_nome: str | None = None,
) -> PayloadValidationResult:
    duracao_ms = int((time.monotonic() - started_at) * 1000)
    erro_tecnico = None
    if not valid:
        erro_tecnico = "; ".join(
            f"{problem['campo']}: esperado '{problem['tipo_esperado']}', "
            f"recebido '{problem['tipo_recebido']}'"
            for problem in problems
        ) or message

    operation_log.append_operation_record(
        operation_log.OperationType.VALIDACAO_PAYLOAD,
        operation_log.OperationResult.SUCESSO if valid else operation_log.OperationResult.ERRO,
        duracao_ms,
        schema=schema_nome,
        erro_tecnico=erro_tecnico,
    )
    return PayloadValidationResult(valid=valid, message=message, problems=problems)


def validate_payload(schema_avsc: str, payload: dict) -> PayloadValidationResult:
    """Valida um payload JSON contra um schema Avro, sem publicar nada
    (US-003a), sobre `avro/validator.py` (TASK-027). Primeiro garante que
    o próprio schema é estruturalmente válido (`avro/schema_loader.py`,
    TASK-021) — pré-condição documentada de `avro/validator.py` — e só
    então valida o payload contra ele. O resultado (sucesso ou lista de
    problemas por campo) é sempre gravado como Registro de Operação
    (TASK-010), nunca deixando uma tentativa de validação sem rastro."""
    started_at = time.monotonic()

    try:
        loaded_schema = schema_loader.load_schema(schema_avsc)
    except AvroSchemaError as error:
        return _record_payload_validation(
            started_at, valid=False, message=error.friendly_message, problems=[]
        )

    problems = avro_validator.validate_payload(schema_avsc, payload)

    if problems:
        problem_dicts = [
            {
                "campo": problem.campo,
                "tipo_esperado": problem.tipo_esperado,
                "tipo_recebido": problem.tipo_recebido,
            }
            for problem in problems
        ]
        return _record_payload_validation(
            started_at,
            valid=False,
            message="Payload inválido: verifique os campos apontados.",
            problems=problem_dicts,
            schema_nome=loaded_schema.nome,
        )

    return _record_payload_validation(
        started_at,
        valid=True,
        message="Payload válido.",
        problems=[],
        schema_nome=loaded_schema.nome,
    )


def _record_publish(
    nome_configuracao: str,
    started_at: float,
    *,
    success: bool,
    message: str,
    topic: str,
    schema_nome: str | None = None,
    partition: int | None = None,
    offset: int | None = None,
    key: str | None = None,
    technical_detail: str = "",
) -> PublishResult:
    duracao_ms = int((time.monotonic() - started_at) * 1000)
    operation_log.append_operation_record(
        operation_log.OperationType.PUBLICACAO,
        operation_log.OperationResult.SUCESSO if success else operation_log.OperationResult.ERRO,
        duracao_ms,
        configuracao=nome_configuracao,
        topic=topic,
        schema=schema_nome,
        partition=partition,
        offset=offset,
        key=key,
        erro_tecnico=None if success else technical_detail,
    )
    return PublishResult(
        success=success, message=message, topic=topic, partition=partition, offset=offset
    )


def publish(
    nome_configuracao: str,
    topic: str,
    schema_avsc: str,
    payload: dict,
    key: str | None = None,
) -> PublishResult:
    """Orquestra validar → serializar → (Schema Registry, se configurado) →
    publicar → registrar operação (US-003b/US-004a, FR-020/FR-021). Único
    caminho de código usado tanto pela UI quanto pela API para publicar
    mensagens (NFR-006), sobre `avro/validator.py`, `kafka/serializer.py`
    (TASK-032) e `kafka/producer.py` (TASK-033). Um payload inválido é
    bloqueado antes de qualquer tentativa de publicação (cenário 3 de
    US-003b); funciona apenas com o `.avsc` local, sem exigir Schema
    Registry (cenário 4, FR-007) — o uso do Schema Registry na serialização
    é adicionado por TASK-049, sem mudar esta assinatura."""
    started_at = time.monotonic()
    configuration = _get_configuration_snapshot(nome_configuracao)

    def _failure(
        message: str, *, schema_nome: str | None = None, technical_detail: str = ""
    ) -> PublishResult:
        return _record_publish(
            nome_configuracao,
            started_at,
            success=False,
            message=message,
            topic=topic,
            schema_nome=schema_nome,
            key=key,
            technical_detail=technical_detail,
        )

    try:
        loaded_schema = schema_loader.load_schema(schema_avsc)
    except AvroSchemaError as error:
        return _failure(error.friendly_message, technical_detail=error.technical_detail)

    problems = avro_validator.validate_payload(schema_avsc, payload)
    if problems:
        technical_detail = "; ".join(
            f"{problem.campo}: esperado '{problem.tipo_esperado}', "
            f"recebido '{problem.tipo_recebido}'"
            for problem in problems
        )
        return _failure(
            "Payload inválido: verifique os campos apontados.",
            schema_nome=loaded_schema.nome,
            technical_detail=technical_detail,
        )

    schema_id = None
    if configuration.schema_registry is not None:
        # FR-015/TASK-049: usa o schema id do Schema Registry na
        # serialização quando configurado — `register_or_reuse_schema`
        # já reaproveita o id existente para um schema idêntico
        # (SC-008), nunca criando uma versão duplicada.
        try:
            schema_id = registry_client.register_or_reuse_schema(
                configuration.schema_registry, loaded_schema.nome, schema_avsc
            )
        except SchemaRegistryError as error:
            return _failure(
                error.friendly_message,
                schema_nome=loaded_schema.nome,
                technical_detail=error.technical_detail,
            )

    try:
        serialized = kafka_serializer.serialize(schema_avsc, payload, schema_id=schema_id)
    except MessageSerializationError as error:
        return _failure(
            error.friendly_message,
            schema_nome=loaded_schema.nome,
            technical_detail=error.technical_detail,
        )

    try:
        partition, offset = kafka_producer.produce(configuration, topic, serialized, key=key)
    except (KafkaAuthenticationError, MessagePublishError) as error:
        return _failure(
            error.friendly_message,
            schema_nome=loaded_schema.nome,
            technical_detail=error.technical_detail,
        )
    except KafkaException as error:
        message, technical_detail = _describe_kafka_error(error.args[0])
        return _failure(message, schema_nome=loaded_schema.nome, technical_detail=technical_detail)

    return _record_publish(
        nome_configuracao,
        started_at,
        success=True,
        message="Mensagem publicada com sucesso.",
        topic=topic,
        schema_nome=loaded_schema.nome,
        partition=partition,
        offset=offset,
        key=key,
    )


def get_dashboard_status() -> DashboardStatus:
    """Resume o estado da ferramenta para a tela inicial (US-007a, FR-023,
    TASK-053). "Configuração ativa" (achado S1 de `analysis.md`: a spec
    não define nenhum mecanismo de "ativar" uma configuração) é definida
    aqui como a configuração referenciada pela operação mais recente do
    histórico — sem exigir nenhum campo/estado adicional. Os status de
    Kafka/Schema Registry vêm do teste mais recente já registrado para
    essa configuração (TASK-017/TASK-046), sem disparar um novo teste de
    rede a cada abertura da tela. Tudo derivado do log diário de operações
    (`services/operation_log.py`) e do armazenamento local de schemas —
    nenhum banco de dados ou índice adicional."""
    recent_operations = operation_log.read_recent_operations()

    active_configuration = next(
        (record.configuracao for record in recent_operations if record.configuracao), None
    )

    def _last_result(tipo: operation_log.OperationType) -> bool | None:
        if active_configuration is None:
            return None
        return next(
            (
                record.resultado is operation_log.OperationResult.SUCESSO
                for record in recent_operations
                if record.tipo_operacao is tipo and record.configuracao == active_configuration
            ),
            None,
        )

    last_publish = next(
        (
            record
            for record in recent_operations
            if record.tipo_operacao is operation_log.OperationType.PUBLICACAO
            and record.resultado is operation_log.OperationResult.SUCESSO
        ),
        None,
    )

    return DashboardStatus(
        active_configuration=active_configuration,
        kafka_connected=_last_result(operation_log.OperationType.TESTE_CONEXAO),
        schema_registry_connected=_last_result(operation_log.OperationType.TESTE_SCHEMA_REGISTRY),
        schemas_loaded=count_schemas(),
        last_publish_topic=last_publish.topic if last_publish else None,
        last_publish_partition=last_publish.partition if last_publish else None,
        last_publish_offset=last_publish.offset if last_publish else None,
    )


def list_recent_operations(
    *,
    tipo: operation_log.OperationType | None = None,
    resultado: operation_log.OperationResult | None = None,
    limit: int = 200,
) -> list[operation_log.OperationRecord]:
    """Histórico de operações para a tela de Logs (US-007b, FR-024/FR-025,
    TASK-056) e para `GET /api/v1/logs` (TASK-057) — mesma fonte usada por
    `get_dashboard_status`, sem exigir nenhum banco de dados."""
    records = operation_log.read_recent_operations()
    if tipo is not None:
        records = [record for record in records if record.tipo_operacao is tipo]
    if resultado is not None:
        records = [record for record in records if record.resultado is resultado]
    return records[:limit]
