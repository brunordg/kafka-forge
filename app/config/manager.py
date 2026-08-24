import json
from pathlib import Path

from app.config.models import EnvironmentConfiguration
from app.config.storage import CONFIGURATIONS_FILENAME, ensure_storage_structure
from app.exceptions import ConfigurationAlreadyExistsError, ConfigurationNotFoundError


def _configurations_file() -> Path:
    base_dir = ensure_storage_structure()
    return base_dir / CONFIGURATIONS_FILENAME


def _read_all() -> list[dict]:
    content = _configurations_file().read_text().strip()
    return json.loads(content) if content else []


def _write_all(raw_configurations: list[dict]) -> None:
    _configurations_file().write_text(json.dumps(raw_configurations, indent=2, ensure_ascii=False))


def _not_found(nome: str) -> ConfigurationNotFoundError:
    return ConfigurationNotFoundError(
        f"Configuração '{nome}' não encontrada.",
        f"Nenhum registro com nome={nome!r} em {CONFIGURATIONS_FILENAME}",
    )


def _already_exists(nome: str) -> ConfigurationAlreadyExistsError:
    return ConfigurationAlreadyExistsError(
        f"Já existe uma configuração chamada '{nome}'.",
        f"Tentativa de gravar configuração duplicada: nome={nome!r}",
    )


def list_configurations() -> list[EnvironmentConfiguration]:
    return [EnvironmentConfiguration.model_validate(item) for item in _read_all()]


def get_configuration(nome: str) -> EnvironmentConfiguration:
    for item in _read_all():
        if item.get("nome") == nome:
            return EnvironmentConfiguration.model_validate(item)
    raise _not_found(nome)


def create_configuration(configuration: EnvironmentConfiguration) -> EnvironmentConfiguration:
    raw_configurations = _read_all()
    if any(item.get("nome") == configuration.nome for item in raw_configurations):
        raise _already_exists(configuration.nome)

    raw_configurations.append(configuration.model_dump(mode="json"))
    _write_all(raw_configurations)
    return configuration


def update_configuration(nome: str, configuration: EnvironmentConfiguration) -> EnvironmentConfiguration:
    raw_configurations = _read_all()
    index = next(
        (i for i, item in enumerate(raw_configurations) if item.get("nome") == nome),
        None,
    )
    if index is None:
        raise _not_found(nome)

    renamed = configuration.nome != nome
    if renamed and any(item.get("nome") == configuration.nome for item in raw_configurations):
        raise _already_exists(configuration.nome)

    raw_configurations[index] = configuration.model_dump(mode="json")
    _write_all(raw_configurations)
    return configuration


def delete_configuration(nome: str) -> None:
    raw_configurations = _read_all()
    remaining = [item for item in raw_configurations if item.get("nome") != nome]
    if len(remaining) == len(raw_configurations):
        raise _not_found(nome)

    _write_all(remaining)
