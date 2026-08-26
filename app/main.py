import os

import uvicorn
from fastapi import FastAPI
from nicegui import app as nicegui_app
from nicegui import ui
from nicegui.helpers import is_pytest

import app.ui.pages  # noqa: F401
from app.api.routes import api_router
from app.config.storage import ensure_storage_structure

APP_HOST = "127.0.0.1"
APP_PORT = int(os.environ.get("APP_PORT", "8080"))

ensure_storage_structure()

nicegui_app.colors(
    primary="#4f46e5",
    secondary="#64748b",
    accent="#4f46e5",
    positive="#16a34a",
    negative="#dc2626",
    info="#0ea5e9",
    warning="#f59e0b",
)

app = FastAPI(title="KafkaForge", docs_url="/docs")
app.include_router(api_router)

ui.run_with(app)

if __name__ in {"__main__", "__mp_main__"} and not is_pytest():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
