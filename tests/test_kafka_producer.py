import pytest
from confluent_kafka import KafkaError

from app.config.models import EnvironmentConfiguration, KafkaConfig, SecurityProtocol
from app.exceptions import MessagePublishError
from app.kafka import producer


class _FakeMessage:
    def __init__(self, partition: int, offset: int):
        self._partition = partition
        self._offset = offset

    def partition(self) -> int:
        return self._partition

    def offset(self) -> int:
        return self._offset


class _FakeProducer:
    def __init__(self, *, error: KafkaError | None = None, remaining: int = 0):
        self._error = error
        self._remaining = remaining
        self.produce_calls: list[dict] = []

    def produce(self, topic, value=None, key=None, on_delivery=None):
        self.produce_calls.append({"topic": topic, "value": value, "key": key})
        if on_delivery is not None and self._remaining == 0:
            on_delivery(self._error, _FakeMessage(2, 12345))

    def flush(self, timeout=None) -> int:
        return self._remaining


def _configuration() -> EnvironmentConfiguration:
    return EnvironmentConfiguration(
        nome="Desenvolvimento",
        kafka=KafkaConfig(bootstrap_servers="localhost:9092", security_protocol=SecurityProtocol.PLAINTEXT),
    )


def _patch_producer(monkeypatch, fake_producer: _FakeProducer) -> None:
    monkeypatch.setattr(producer.kafka_connection, "build_producer", lambda configuration: fake_producer)


def test_produce_returns_partition_and_offset_from_the_delivery_report(monkeypatch):
    _patch_producer(monkeypatch, _FakeProducer())

    partition, offset = producer.produce(_configuration(), "pedido-criado", b"payload")

    assert (partition, offset) == (2, 12345)


def test_produce_encodes_the_key_as_bytes(monkeypatch):
    fake_producer = _FakeProducer()
    _patch_producer(monkeypatch, fake_producer)

    producer.produce(_configuration(), "pedido-criado", b"payload", key="abc")

    assert fake_producer.produce_calls[0]["key"] == b"abc"


def test_produce_raises_message_publish_error_for_an_unknown_topic(monkeypatch):
    error = KafkaError(KafkaError.UNKNOWN_TOPIC_OR_PART, "Simulação: tópico inexistente")
    _patch_producer(monkeypatch, _FakeProducer(error=error))

    with pytest.raises(MessagePublishError) as exc_info:
        producer.produce(_configuration(), "topico-inexistente", b"payload")

    assert "tópico informado não existe" in exc_info.value.friendly_message.lower()


def test_produce_raises_message_publish_error_when_connection_is_lost(monkeypatch):
    error = KafkaError(KafkaError._TRANSPORT, "Simulação: conexão perdida")
    _patch_producer(monkeypatch, _FakeProducer(error=error))

    with pytest.raises(MessagePublishError) as exc_info:
        producer.produce(_configuration(), "pedido-criado", b"payload")

    assert "conexão" in exc_info.value.friendly_message.lower()


def test_produce_raises_message_publish_error_on_flush_timeout(monkeypatch):
    # nunca reporta sucesso sem confirmação do broker (edge case da spec)
    _patch_producer(monkeypatch, _FakeProducer(remaining=1))

    with pytest.raises(MessagePublishError):
        producer.produce(_configuration(), "pedido-criado", b"payload")
