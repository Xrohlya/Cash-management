import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from database.db import init_db
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings
from backend.auth import verify_init_data
from backend.webapp import webapp_html
from backend.routes import dashboard, operations, settings as settings_routes, accounts, sources, recurring, siri, planning

WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cash Management API", version="2.0.0", lifespan=lifespan)
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Telegram-Init-Data"],
    )
app.mount("/static", StaticFiles(directory=WEBAPP_DIR / "static"), name="static")

for routes in (dashboard, operations, settings_routes, accounts, sources, recurring, siri, planning):
    app.include_router(routes.router)


@app.get("/", include_in_schema=False)
def webapp():
    return HTMLResponse(
        webapp_html(),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/health")
def health():
    return {
        "ok": True,
        "version": "2.0.0",
        "commit": os.getenv("RENDER_GIT_COMMIT", "local")[:7],
    }
