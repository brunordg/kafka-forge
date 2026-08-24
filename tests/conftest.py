import os
import runpy
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nicegui.testing.general import nicegui_reset_globals

# Evita que a simples coleta/execução dos testes toque o ~/.kafkaforge real
# da máquina antes que qualquer fixture por teste tenha a chance de isolar
# KAFKAFORGE_HOME — o `ensure_storage_structure()` de nível de módulo em
# `app/main.py` roda assim que o arquivo é (re)importado, inclusive pela
# fixture `api_client` abaixo.
os.environ.setdefault("KAFKAFORGE_HOME", tempfile.mkdtemp(prefix="kafkaforge-tests-"))

_MAIN_FILE = Path(__file__).resolve().parent.parent / "app" / "main.py"


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch, tmp_path):
    """Isola o armazenamento local (TASK-006) por teste, apontando
    KAFKAFORGE_HOME para um diretório temporário novo a cada teste."""
    monkeypatch.setenv("KAFKAFORGE_HOME", str(tmp_path / ".kafkaforge"))


@pytest.fixture
def api_client(monkeypatch):
    """`TestClient` para o `app` real de `app/main.py`, reconstruído do
    zero a cada teste com o mesmo protocolo de reset usado pelo fixture
    `user` do NiceGUI (`nicegui_reset_globals`).

    Necessário porque `core.app` — o registro interno de páginas do
    NiceGUI, montado dentro do nosso `app` via `ui.run_with` (TASK-004) —
    é um singleton de todo o processo. Sem reconstruir tudo a cada teste,
    testes que usam o fixture `user` (simulação de UI, TASK-014) e testes
    que importavam `app.main` uma única vez no topo do arquivo corrompiam
    o estado um do outro dependendo da ordem de execução dos arquivos de
    teste (ex.: `core.app.config` ficava sem os valores de
    `ui.run_with(...)`, quebrando até respostas 404 do NiceGUI).
    """
    monkeypatch.setenv("NICEGUI_USER_SIMULATION", "true")
    with nicegui_reset_globals():
        module_globals = runpy.run_path(str(_MAIN_FILE), run_name="__main__")
        app: FastAPI = module_globals["app"]
        with TestClient(app) as client:
            yield client
