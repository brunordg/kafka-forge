import os
from pathlib import Path

BASE_DIR_ENV_VAR = "KAFKAFORGE_HOME"
DEFAULT_BASE_DIR = Path.home() / ".kafkaforge"

DIR_MODE = 0o700
FILE_MODE = 0o600

CONFIGURATIONS_FILENAME = "configurations.json"
SCHEMAS_DIRNAME = "schemas"
LOGS_DIRNAME = "logs"


def get_base_dir() -> Path:
    configured = os.environ.get(BASE_DIR_ENV_VAR)
    return Path(configured).expanduser() if configured else DEFAULT_BASE_DIR


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, DIR_MODE)


def _ensure_file(path: Path, initial_content: str) -> None:
    if not path.exists():
        path.write_text(initial_content)
    os.chmod(path, FILE_MODE)


def ensure_storage_structure() -> Path:
    base_dir = get_base_dir()
    _ensure_dir(base_dir)
    _ensure_dir(base_dir / SCHEMAS_DIRNAME)
    _ensure_dir(base_dir / LOGS_DIRNAME)
    _ensure_file(base_dir / CONFIGURATIONS_FILENAME, "[]")
    return base_dir
