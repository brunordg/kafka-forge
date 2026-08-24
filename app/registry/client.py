import tempfile
from contextlib import contextmanager
from pathlib import Path

from confluent_kafka.schema_registry import Schema, SchemaRegistryClient

from app.config.models import SchemaRegistryConfig
from app.exceptions import SchemaRegistryError

# Decisão Q2 (seção 7 do plano): 10 segundos — mesmo timeout usado para
# testar a conexão Kafka e para publicar.
REQUEST_TIMEOUT_SECONDS = 10


def _write_temp_pem(content: str) -> str:
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
    handle.write(content)
    handle.close()
    return handle.name


def _build_client_config(config: SchemaRegistryConfig) -> tuple[dict, list[str]]:
    """Monta a configuração do `SchemaRegistryClient` da Confluent a partir
    de uma `SchemaRegistryConfig` (US-005a, FR-005/FR-006). Diferente de
    `kafka/connection.py` (que aceita PEM em memória para o Kafka via
    `librdkafka`), o cliente HTTP do Schema Registry só aceita caminho de
    arquivo para SSL (`ssl.ca.location`/`ssl.certificate.location`/
    `ssl.key.location`) — os certificados são gravados em arquivos
    temporários, cujos caminhos são devolvidos para remoção pelo chamador
    logo após o uso (`_client`)."""
    conf: dict = {"url": config.url, "timeout": REQUEST_TIMEOUT_SECONDS}
    temp_files: list[str] = []

    if config.username is not None and config.password is not None:
        conf["basic.auth.user.info"] = f"{config.username}:{config.password}"

    if config.ca_cert is not None:
        path = _write_temp_pem(config.ca_cert)
        temp_files.append(path)
        conf["ssl.ca.location"] = path
    if config.client_cert is not None:
        path = _write_temp_pem(config.client_cert)
        temp_files.append(path)
        conf["ssl.certificate.location"] = path
    if config.client_key is not None:
        path = _write_temp_pem(config.client_key)
        temp_files.append(path)
        conf["ssl.key.location"] = path

    return conf, temp_files


@contextmanager
def _client(config: SchemaRegistryConfig):
    conf, temp_files = _build_client_config(config)
    try:
        yield SchemaRegistryClient(conf)
    finally:
        for path in temp_files:
            Path(path).unlink(missing_ok=True)


def test_connection(config: SchemaRegistryConfig) -> None:
    """Verifica se o Schema Registry está acessível, sem efeitos colaterais
    sobre ele (US-005a, NFR-002) — `get_subjects()` é uma chamada somente
    de leitura, nunca registra nem altera nada. Levanta `SchemaRegistryError`
    com mensagem compreensível em caso de falha (cenário 2 de US-005a)."""
    try:
        with _client(config) as client:
            client.get_subjects()
    except SchemaRegistryError:
        raise
    except Exception as error:
        raise SchemaRegistryError(
            "Não foi possível conectar ao Schema Registry informado.", str(error)
        ) from error


def list_subjects(config: SchemaRegistryConfig) -> list[str]:
    """US-005b, cenário 1: lista os subjects existentes no Schema Registry
    configurado."""
    try:
        with _client(config) as client:
            return client.get_subjects()
    except Exception as error:
        raise SchemaRegistryError(
            "Não foi possível consultar os subjects do Schema Registry.", str(error)
        ) from error


def list_versions(config: SchemaRegistryConfig, subject: str) -> list[int]:
    try:
        with _client(config) as client:
            return client.get_versions(subject)
    except Exception as error:
        raise SchemaRegistryError(
            f"Não foi possível consultar as versões do subject '{subject}'.", str(error)
        ) from error


def get_schema(config: SchemaRegistryConfig, subject: str, version: int | str = "latest") -> str:
    """Retorna o conteúdo `.avsc` de uma versão de um subject (US-005b,
    FR-019), usável nos mesmos fluxos de validação/publicação que um
    `.avsc` local carregado por upload."""
    try:
        with _client(config) as client:
            return client.get_version(subject, version).schema.schema_str
    except Exception as error:
        raise SchemaRegistryError(
            f"Não foi possível obter o schema '{subject}' (versão {version}).", str(error)
        ) from error


def register_or_reuse_schema(config: SchemaRegistryConfig, subject: str, avsc_content: str) -> int:
    """Registra `avsc_content` no `subject` informado e retorna o schema id
    (US-005b, TASK-048). `register_schema` da Confluent já é idempotente
    para um schema idêntico a uma versão já registrada — devolve o id
    existente em vez de criar uma versão nova (FR-015/SC-008, edge case da
    spec) —, então não há necessidade de comparação manual de conteúdo
    aqui."""
    try:
        with _client(config) as client:
            return client.register_schema(subject, Schema(avsc_content, schema_type="AVRO"))
    except Exception as error:
        raise SchemaRegistryError(
            f"Não foi possível registrar o schema no subject '{subject}'.", str(error)
        ) from error
