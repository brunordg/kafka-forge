import stat
from pathlib import Path

from app.config.storage import (
    BASE_DIR_ENV_VAR,
    CONFIGURATIONS_FILENAME,
    LOGS_DIRNAME,
    SCHEMAS_DIRNAME,
    DEFAULT_BASE_DIR,
    ensure_storage_structure,
    get_base_dir,
)


def _permission_bits(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_get_base_dir_defaults_to_home_kafkaforge(monkeypatch):
    monkeypatch.delenv(BASE_DIR_ENV_VAR, raising=False)

    assert get_base_dir() == DEFAULT_BASE_DIR


def test_get_base_dir_honors_env_var(monkeypatch, tmp_path):
    configured = tmp_path / "custom-home"
    monkeypatch.setenv(BASE_DIR_ENV_VAR, str(configured))

    assert get_base_dir() == configured


def test_ensure_storage_structure_creates_missing_tree(monkeypatch, tmp_path):
    base_dir = tmp_path / "kafkaforge-home"
    monkeypatch.setenv(BASE_DIR_ENV_VAR, str(base_dir))

    result = ensure_storage_structure()

    assert result == base_dir
    assert base_dir.is_dir()
    assert (base_dir / SCHEMAS_DIRNAME).is_dir()
    assert (base_dir / LOGS_DIRNAME).is_dir()
    assert (base_dir / CONFIGURATIONS_FILENAME).read_text() == "[]"


def test_ensure_storage_structure_restricts_permissions(monkeypatch, tmp_path):
    base_dir = tmp_path / "kafkaforge-home"
    monkeypatch.setenv(BASE_DIR_ENV_VAR, str(base_dir))

    ensure_storage_structure()

    assert _permission_bits(base_dir) == 0o700
    assert _permission_bits(base_dir / SCHEMAS_DIRNAME) == 0o700
    assert _permission_bits(base_dir / LOGS_DIRNAME) == 0o700
    assert _permission_bits(base_dir / CONFIGURATIONS_FILENAME) == 0o600


def test_ensure_storage_structure_is_idempotent_and_preserves_content(
    monkeypatch, tmp_path
):
    base_dir = tmp_path / "kafkaforge-home"
    monkeypatch.setenv(BASE_DIR_ENV_VAR, str(base_dir))

    ensure_storage_structure()
    configurations_file = base_dir / CONFIGURATIONS_FILENAME
    configurations_file.write_text('[{"nome": "Desenvolvimento"}]')

    ensure_storage_structure()

    assert configurations_file.read_text() == '[{"nome": "Desenvolvimento"}]'
