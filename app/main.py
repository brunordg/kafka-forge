import os

import uvicorn
from fastapi import FastAPI
from nicegui import ui
from nicegui.helpers import is_pytest

import app.ui.pages  # noqa: F401
from app.api.routes import api_router
from app.config.storage import ensure_storage_structure

APP_HOST = "127.0.0.1"
APP_PORT = int(os.environ.get("APP_PORT", "8080"))

ensure_storage_structure()

app = FastAPI(title="KafkaForge", docs_url="/docs")
app.include_router(api_router)

ui.run_with(app)

if __name__ in {"__main__", "__mp_main__"} and not is_pytest():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
