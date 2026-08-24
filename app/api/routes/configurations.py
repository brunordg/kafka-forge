from fastapi import APIRouter, HTTPException, status

from app.api.schemas.configurations import (
    ConfigurationCreateRequest,
    ConfigurationResponse,
    ConfigurationTestResponse,
)
from app.exceptions import ConfigurationAlreadyExistsError, ConfigurationNotFoundError
from app.services import kafka_service

router = APIRouter(prefix="/configurations", tags=["configurations"])


@router.get("", response_model=list[ConfigurationResponse])
def list_configurations() -> list[ConfigurationResponse]:
    configurations = kafka_service.list_configurations()
    return [ConfigurationResponse.from_domain(configuration) for configuration in configurations]


@router.post("", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
def create_configuration(request: ConfigurationCreateRequest) -> ConfigurationResponse:
    try:
        created = kafka_service.create_configuration(request.to_domain())
    except ConfigurationAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.friendly_message,
        ) from error

    return ConfigurationResponse.from_domain(created)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_configuration(name: str) -> None:
    try:
        kafka_service.delete_configuration(name)
    except ConfigurationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.friendly_message,
        ) from error


@router.post("/{name}/test", response_model=ConfigurationTestResponse)
def test_configuration(name: str) -> ConfigurationTestResponse:
    """Testa Kafka e, quando configurado para o ambiente, o Schema Registry
    (US-001b + US-005a, TASK-046) — resultados separados e identificáveis
    na resposta."""
    try:
        result = kafka_service.test_configuration(name)
    except ConfigurationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.friendly_message,
        ) from error

    return ConfigurationTestResponse.from_domain(result)
