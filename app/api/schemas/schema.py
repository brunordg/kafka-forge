from pydantic import BaseModel, field_validator

from app.services.kafka_service import SchemaValidationResult


class SchemaValidateRequest(BaseModel):
    avsc_content: str

    @field_validator("avsc_content")
    @classmethod
    def _avsc_content_obrigatorio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Informe o conteúdo do arquivo .avsc.")
        return value


class SchemaFieldResponse(BaseModel):
    nome: str
    tipo: str


class SchemaValidationResponse(BaseModel):
    valid: bool
    message: str
    nome: str | None = None
    namespace: str | None = None
    fields: list[SchemaFieldResponse] | None = None
    raw_content: str | None = None

    @classmethod
    def from_domain(cls, result: SchemaValidationResult) -> "SchemaValidationResponse":
        return cls(
            valid=result.valid,
            message=result.message,
            nome=result.nome,
            namespace=result.namespace,
            fields=result.fields,
            raw_content=result.raw_content,
        )
