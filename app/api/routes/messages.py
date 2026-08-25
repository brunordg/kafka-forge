from fastapi import APIRouter, HTTPException, status

from app.api.schemas.messages import (
    MessagePublishRequest,
    MessagePublishResponse,
    PayloadValidateRequest,
    PayloadValidationResponse,
)
from app.exceptions import ConfigurationNotFoundError, SchemaNotFoundError
from app.services import kafka_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/validate", response_model=PayloadValidationResponse)
def validate_payload(request: PayloadValidateRequest) -> PayloadValidationResponse:
    result = kafka_service.validate_payload(request.avsc_content, request.payload)
    return PayloadValidationResponse.from_domain(result)


@router.post("", response_model=MessagePublishResponse)
def publish_message(request: MessagePublishRequest) -> MessagePublishResponse:
    """US-003b/US-004a: valida -> serializa -> publica, retornando
    tópico/partição/offset (sucesso) ou um erro compreensível (falha) —
    mesmo `services/kafka_service.py` usado pela UI (NFR-006, SC-005).
    Configuração ou schema inexistentes (cenário 3 de US-004a) viram 404,
    identificando qual dos dois não foi encontrado. `schema` é opcional:
    sem ele, o payload é publicado como JSON puro, sem validação Avro."""
    schema_content = None
    if request.schema_ is not None:
        try:
            schema_content = kafka_service.get_named_schema(request.schema_).raw_content
        except SchemaNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error.friendly_message
            ) from error

    try:
        result = kafka_service.publish(
            request.configuration,
            request.topic,
            schema_content,
            request.payload,
            key=request.key,
        )
    except ConfigurationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.friendly_message
        ) from error

    return MessagePublishResponse.from_domain(result)
