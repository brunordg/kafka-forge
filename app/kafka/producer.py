from confluent_kafka import KafkaError, KafkaException

from app.config.models import EnvironmentConfiguration
from app.exceptions import MessagePublishError
from app.kafka import connection as kafka_connection

# Prefixos de mensagem amigável por nome de erro `librdkafka` observado no
# delivery report — vocabulário diferente do de `kafka_service._describe_
# kafka_error` (aquele é sobre *conectar*; este é sobre *publicar*): um
# tópico inexistente ou uma conexão perdida no meio da publicação (edge
# cases da spec) precisam ser distinguíveis de um erro genérico.
_PUBLISH_ERROR_FRIENDLY_PREFIXES: dict[str, str] = {
    "UNKNOWN_TOPIC_OR_PART": "O tópico informado não existe no cluster Kafka",
    "_TRANSPORT": "A conexão com o Kafka foi perdida durante a publicação",
    "_TIMED_OUT": "Tempo esgotado aguardando a confirmação de entrega pelo Kafka",
    "_MSG_TIMED_OUT": "Tempo esgotado aguardando a confirmação de entrega pelo Kafka",
    "_AUTHENTICATION": "Falha de autenticação ao publicar no Kafka",
    "SASL_AUTHENTICATION_FAILED": "Falha de autenticação SASL ao publicar no Kafka",
    "TOPIC_AUTHORIZATION_FAILED": "Sem autorização para publicar no tópico informado",
    "CLUSTER_AUTHORIZATION_FAILED": "Sem autorização para publicar neste cluster Kafka",
}


def _describe_publish_error(kafka_error: KafkaError) -> tuple[str, str]:
    technical_detail = kafka_error.str()
    prefix = _PUBLISH_ERROR_FRIENDLY_PREFIXES.get(
        kafka_error.name(), "Falha ao publicar a mensagem no Kafka"
    )
    return f"{prefix}: {technical_detail}", technical_detail


def produce(
    configuration: EnvironmentConfiguration,
    topic: str,
    value: bytes,
    key: str | None = None,
) -> tuple[int, int]:
    """Produz a mensagem serializada e aguarda o delivery report (US-003b,
    FR-016/FR-017), respeitando o timeout de 10s (decisão Q2). Nunca
    retorna sucesso sem a confirmação explícita do broker via delivery
    report — uma conexão perdida no meio da publicação vira
    `MessagePublishError`, nunca um resultado silenciosamente bem-sucedido
    (edge case da spec)."""
    producer = kafka_connection.build_producer(configuration)
    delivery: dict = {}

    def _on_delivery(err: KafkaError | None, msg) -> None:
        delivery["err"] = err
        delivery["msg"] = msg

    key_bytes = key.encode("utf-8") if key is not None else None
    try:
        producer.produce(topic, value=value, key=key_bytes, on_delivery=_on_delivery)
    except (KafkaException, BufferError) as error:
        raise MessagePublishError("Falha ao publicar a mensagem no Kafka.", str(error)) from error

    remaining = producer.flush(kafka_connection.CONNECTION_TIMEOUT_MS / 1000)
    if remaining > 0 or "err" not in delivery:
        raise MessagePublishError(
            "Tempo esgotado aguardando a confirmação de entrega da mensagem pelo Kafka.",
            f"producer.flush() retornou {remaining} mensagem(ns) pendente(s) após o timeout.",
        )

    if delivery["err"] is not None:
        message, technical_detail = _describe_publish_error(delivery["err"])
        raise MessagePublishError(message, technical_detail)

    msg = delivery["msg"]
    return msg.partition(), msg.offset()
