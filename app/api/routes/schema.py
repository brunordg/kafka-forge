from fastapi import APIRouter

from app.api.schemas.schema import SchemaValidateRequest, SchemaValidationResponse
from app.services import kafka_service

router = APIRouter(prefix="/schema", tags=["schema"])


@router.post("/validate", response_model=SchemaValidationResponse)
def validate_schema(request: SchemaValidateRequest) -> SchemaValidationResponse:
    result = kafka_service.validate_schema(request.avsc_content)
    return SchemaValidationResponse.from_domain(result)
