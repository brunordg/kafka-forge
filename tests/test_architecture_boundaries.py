import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESTRICTED_PACKAGES = ("app/ui", "app/api")
FORBIDDEN_MODULES = {"kafka", "avro", "registry"}
# ("config", "manager"): a lógica de CRUD de configurações (TASK-008) só
# pode ser chamada a partir de `services/kafka_service.py` (TASK-013) —
# `config.models`/`config.storage` continuam liberados, pois são apenas
# definições de dados, não orquestração/E/S.
FORBIDDEN_SUBPATHS = {("config", "manager")}


def _strip_app_prefix(parts: list[str]) -> list[str]:
    return parts[1:] if parts[:1] == ["app"] else parts


def _forbidden_from_dotted_path(dotted_name: str) -> set[str]:
    parts = _strip_app_prefix(dotted_name.split("."))
    if not parts:
        return set()

    targets = set()
    if parts[0] in FORBIDDEN_MODULES:
        targets.add(parts[0])
    if len(parts) > 1 and tuple(parts[:2]) in FORBIDDEN_SUBPATHS:
        targets.add(".".join(parts[:2]))
    return targets


def _forbidden_imports(source: str) -> set[str]:
    tree = ast.parse(source)
    forbidden: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                forbidden |= _forbidden_from_dotted_path(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            forbidden |= _forbidden_from_dotted_path(node.module)
            module_parts = _strip_app_prefix(node.module.split("."))
            for alias in node.names:
                forbidden |= _forbidden_from_dotted_path(".".join([*module_parts, alias.name]))
    return forbidden


def test_detects_import_of_forbidden_top_level_module():
    assert _forbidden_imports("import kafka") == {"kafka"}
    assert _forbidden_imports("import app.kafka.connection") == {"kafka"}


def test_detects_from_import_of_forbidden_top_level_module():
    assert _forbidden_imports("from kafka.connection import build_producer") == {"kafka"}
    assert _forbidden_imports("from app.kafka.connection import build_producer") == {"kafka"}
    assert _forbidden_imports("from app.kafka import connection") == {"kafka"}
    assert _forbidden_imports("from app.avro import validator") == {"avro"}
    assert _forbidden_imports("from app.registry import client") == {"registry"}


def test_detects_config_manager_regardless_of_import_style():
    assert _forbidden_imports("import app.config.manager") == {"config.manager"}
    assert _forbidden_imports("from app.config.manager import get_configuration") == {
        "config.manager"
    }
    assert _forbidden_imports("from app.config import manager") == {"config.manager"}


def test_does_not_flag_config_models_or_config_storage():
    assert _forbidden_imports("from app.config.models import EnvironmentConfiguration") == set()
    assert _forbidden_imports("from app.config.storage import ensure_storage_structure") == set()
    assert _forbidden_imports("from app.config import models") == set()


def test_does_not_flag_unrelated_third_party_imports():
    # fastavro é uma dependência legítima do projeto e não deve colidir
    # com o segmento proibido "avro".
    assert _forbidden_imports("import fastavro") == set()
    assert _forbidden_imports("from fastavro import validate") == set()
    assert _forbidden_imports("from app.services import kafka_service") == set()


def test_ui_and_api_never_import_kafka_avro_registry_or_config_manager_directly():
    violations = []

    for package in RESTRICTED_PACKAGES:
        package_dir = PROJECT_ROOT / package
        for py_file in sorted(package_dir.rglob("*.py")):
            forbidden = _forbidden_imports(py_file.read_text())
            if forbidden:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: {sorted(forbidden)}")

    assert not violations, (
        "ui/ e api/ só podem chamar services/kafka_service.py — nunca "
        "kafka/, avro/, registry/ ou config.manager diretamente (NFR-006). "
        "Violações encontradas:\n" + "\n".join(violations)
    )
