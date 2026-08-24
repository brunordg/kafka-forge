import os
from pathlib import Path

from app.avro.schema_loader import LoadedAvroSchema, load_schema
from app.config.storage import FILE_MODE, SCHEMAS_DIRNAME, ensure_storage_structure
from app.exceptions import SchemaNotFoundError

_EXTENSION = ".avsc"


def _schemas_dir() -> Path:
    base_dir = ensure_storage_structure()
    return base_dir / SCHEMAS_DIRNAME


def _schema_file(nome: str) -> Path:
    return _schemas_dir() / f"{nome}{_EXTENSION}"


def save_schema(loaded_schema: LoadedAvroSchema) -> LoadedAvroSchema:
    """Persiste um schema já validado (`avro/schema_loader.py`) sob o nome
    declarado no próprio `.avsc`, para que possa ser referenciado por nome
    depois — pela tela Publicar Mensagem e pela API (`POST /api/v1/messages`,
    contrato `"schema": "Pedido"` do briefing/plano §6.1)."""
    schema_file = _schema_file(loaded_schema.nome)
    schema_file.write_text(loaded_schema.raw_content)
    os.chmod(schema_file, FILE_MODE)
    return loaded_schema


def get_schema(nome: str) -> LoadedAvroSchema:
    schema_file = _schema_file(nome)
    if not schema_file.exists():
        raise SchemaNotFoundError(
            f"Schema '{nome}' não encontrado.",
            f"Nenhum arquivo {schema_file.name} em {_schemas_dir()}",
        )
    return load_schema(schema_file.read_text())


def list_schemas() -> list[LoadedAvroSchema]:
    return [
        load_schema(schema_file.read_text())
        for schema_file in sorted(_schemas_dir().glob(f"*{_EXTENSION}"))
    ]


def count_schemas() -> int:
    return len(list(_schemas_dir().glob(f"*{_EXTENSION}")))
