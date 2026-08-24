import pytest

from app.exceptions import (
    AvroSchemaError,
    AvroValidationError,
    KafkaAuthenticationError,
    KafkaAuthorizationError,
    KafkaConnectionError,
    KafkaForgeError,
    MessagePublishError,
    MessageSerializationError,
    SchemaRegistryError,
)

ALL_EXCEPTION_TYPES = [
    KafkaConnectionError,
    KafkaAuthenticationError,
    KafkaAuthorizationError,
    SchemaRegistryError,
    AvroSchemaError,
    AvroValidationError,
    MessageSerializationError,
    MessagePublishError,
]


@pytest.mark.parametrize("exception_type", ALL_EXCEPTION_TYPES)
def test_exception_exposes_friendly_message_and_technical_detail(exception_type):
    try:
        raise exception_type(
            "mensagem compreensível para o desenvolvedor",
            "stack trace bruto do broker",
        )
    except exception_type as error:
        assert error.friendly_message == "mensagem compreensível para o desenvolvedor"
        assert error.technical_detail == "stack trace bruto do broker"


@pytest.mark.parametrize("exception_type", ALL_EXCEPTION_TYPES)
def test_exception_is_subclass_of_kafkaforge_error(exception_type):
    assert issubclass(exception_type, KafkaForgeError)


def test_technical_detail_defaults_to_empty_string():
    try:
        raise KafkaConnectionError("broker inacessível")
    except KafkaConnectionError as error:
        assert error.friendly_message == "broker inacessível"
        assert error.technical_detail == ""


# --- cenário 3 de US-001b: certificado de cliente sem senha de chave
# privada, isolado de app/kafka/connection.py e de qualquer broker real ---


def test_missing_client_key_password_is_a_kafka_authentication_error():
    error = KafkaAuthenticationError.missing_client_key_password()

    assert isinstance(error, KafkaAuthenticationError)


def test_missing_client_key_password_identifies_the_field_explicitly():
    error = KafkaAuthenticationError.missing_client_key_password()

    assert "client_key_password" in error.friendly_message
    # não deve ser um erro genérico de SSL sem contexto
    assert "SSL" not in error.friendly_message.upper()


def test_missing_client_key_password_carries_the_given_technical_detail():
    error = KafkaAuthenticationError.missing_client_key_password("detalhe técnico bruto")

    assert error.technical_detail == "detalhe técnico bruto"


def test_missing_client_key_password_technical_detail_defaults_to_empty_string():
    error = KafkaAuthenticationError.missing_client_key_password()

    assert error.technical_detail == ""


def test_missing_client_key_password_can_be_raised_and_caught_normally():
    with pytest.raises(KafkaAuthenticationError) as exc_info:
        raise KafkaAuthenticationError.missing_client_key_password("detalhe")

    assert "client_key_password" in exc_info.value.friendly_message
    assert exc_info.value.technical_detail == "detalhe"


# --- FR-013 / US-003a: AvroValidationError carrega campo, tipo esperado
# e tipo recebido no detalhe estruturado, isolado de app/avro/validator.py
# e de qualquer schema/payload real ---


def test_avro_validation_error_structured_fields_default_to_none():
    error = AvroValidationError("mensagem genérica")

    assert error.campo is None
    assert error.tipo_esperado is None
    assert error.tipo_recebido is None


def test_field_type_mismatch_is_an_avro_validation_error():
    error = AvroValidationError.field_type_mismatch("valor", "double", "string")

    assert isinstance(error, AvroValidationError)


def test_field_type_mismatch_carries_the_structured_detail():
    error = AvroValidationError.field_type_mismatch("valor", "double", "string")

    assert error.campo == "valor"
    assert error.tipo_esperado == "double"
    assert error.tipo_recebido == "string"


def test_field_type_mismatch_identifies_the_field_in_the_friendly_message():
    error = AvroValidationError.field_type_mismatch("valor", "double", "string")

    assert "valor" in error.friendly_message
    assert "double" in error.friendly_message
    assert "string" in error.friendly_message


def test_field_type_mismatch_carries_the_given_technical_detail():
    error = AvroValidationError.field_type_mismatch(
        "valor", "double", "string", "detalhe técnico bruto"
    )

    assert error.technical_detail == "detalhe técnico bruto"


def test_field_type_mismatch_technical_detail_defaults_to_empty_string():
    error = AvroValidationError.field_type_mismatch("valor", "double", "string")

    assert error.technical_detail == ""


def test_field_type_mismatch_can_be_raised_and_caught_normally():
    with pytest.raises(AvroValidationError) as exc_info:
        raise AvroValidationError.field_type_mismatch("valor", "double", "string")

    assert exc_info.value.campo == "valor"
    assert exc_info.value.tipo_esperado == "double"
    assert exc_info.value.tipo_recebido == "string"
