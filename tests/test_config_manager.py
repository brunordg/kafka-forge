import pytest

from app.config import manager
from app.config.models import EnvironmentConfiguration, KafkaConfig, SecurityProtocol
from app.exceptions import ConfigurationAlreadyExistsError, ConfigurationNotFoundError


def _configuration(nome: str, bootstrap_servers: str = "localhost:9092") -> EnvironmentConfiguration:
    return EnvironmentConfiguration(
        nome=nome,
        kafka=KafkaConfig(
            bootstrap_servers=bootstrap_servers,
            security_protocol=SecurityProtocol.PLAINTEXT,
        ),
    )


def test_list_configurations_starts_empty():
    assert manager.list_configurations() == []


def test_create_and_list_configuration():
    manager.create_configuration(_configuration("Desenvolvimento"))

    configurations = manager.list_configurations()

    assert [c.nome for c in configurations] == ["Desenvolvimento"]


def test_create_and_get_configuration():
    manager.create_configuration(_configuration("Desenvolvimento", "dev:9092"))

    found = manager.get_configuration("Desenvolvimento")

    assert found.kafka.bootstrap_servers == "dev:9092"


def test_get_unknown_configuration_raises_not_found():
    with pytest.raises(ConfigurationNotFoundError) as exc_info:
        manager.get_configuration("Inexistente")

    assert "Inexistente" in exc_info.value.friendly_message
    assert exc_info.value.technical_detail


def test_create_duplicate_name_is_rejected():
    manager.create_configuration(_configuration("Desenvolvimento"))

    with pytest.raises(ConfigurationAlreadyExistsError) as exc_info:
        manager.create_configuration(_configuration("Desenvolvimento"))

    assert "Desenvolvimento" in exc_info.value.friendly_message
    assert manager.list_configurations()[0].kafka.bootstrap_servers == "localhost:9092"


def test_create_duplicate_name_does_not_overwrite_existing_entry():
    manager.create_configuration(_configuration("Desenvolvimento", "original:9092"))

    with pytest.raises(ConfigurationAlreadyExistsError):
        manager.create_configuration(_configuration("Desenvolvimento", "outro:9092"))

    assert manager.get_configuration("Desenvolvimento").kafka.bootstrap_servers == "original:9092"


def test_update_configuration_changes_only_target_entry():
    manager.create_configuration(_configuration("Desenvolvimento", "dev:9092"))
    manager.create_configuration(_configuration("Homologação", "hml:9092"))
    manager.create_configuration(_configuration("Produção", "prod:9092"))

    manager.update_configuration("Homologação", _configuration("Homologação", "hml-novo:9092"))

    assert manager.get_configuration("Desenvolvimento").kafka.bootstrap_servers == "dev:9092"
    assert manager.get_configuration("Homologação").kafka.bootstrap_servers == "hml-novo:9092"
    assert manager.get_configuration("Produção").kafka.bootstrap_servers == "prod:9092"


def test_update_unknown_configuration_raises_not_found():
    with pytest.raises(ConfigurationNotFoundError):
        manager.update_configuration("Inexistente", _configuration("Inexistente"))


def test_update_renaming_to_existing_name_is_rejected():
    manager.create_configuration(_configuration("Desenvolvimento"))
    manager.create_configuration(_configuration("Homologação"))

    with pytest.raises(ConfigurationAlreadyExistsError):
        manager.update_configuration("Desenvolvimento", _configuration("Homologação"))

    # a configuração original não deve ter sido afetada pela tentativa
    assert manager.get_configuration("Desenvolvimento").nome == "Desenvolvimento"


def test_update_can_rename_to_a_free_name():
    manager.create_configuration(_configuration("Antigo Nome", "dev:9092"))

    manager.update_configuration("Antigo Nome", _configuration("Novo Nome", "dev:9092"))

    assert manager.get_configuration("Novo Nome").kafka.bootstrap_servers == "dev:9092"
    with pytest.raises(ConfigurationNotFoundError):
        manager.get_configuration("Antigo Nome")


def test_delete_configuration_removes_only_target_entry():
    manager.create_configuration(_configuration("Desenvolvimento"))
    manager.create_configuration(_configuration("Homologação"))

    manager.delete_configuration("Desenvolvimento")

    with pytest.raises(ConfigurationNotFoundError):
        manager.get_configuration("Desenvolvimento")
    assert manager.get_configuration("Homologação").nome == "Homologação"


def test_delete_unknown_configuration_raises_not_found():
    with pytest.raises(ConfigurationNotFoundError):
        manager.delete_configuration("Inexistente")
