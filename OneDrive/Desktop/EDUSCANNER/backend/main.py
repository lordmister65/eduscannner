from pathlib import Path
import os
import warnings
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from backend.db import init_db
from backend.routes.auth import router as auth_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.classes import router as classes_router
from backend.routes.cards import router as cards_router
from backend.routes.scanner import router as scanner_router
from backend.routes.reports import router as reports_router

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

ENV = os.getenv("ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
if ENV == "production" and SECRET_KEY == "dev-secret-change-me":
    # Não impede o app de subir (evita derrubar um deploy por engano),
    # mas deixa bem claro no log que a sessão não está protegida de
    # verdade — SECRET_KEY previsível permite forjar cookies de sessão.
    warnings.warn(
        "SECRET_KEY está usando o valor padrão de desenvolvimento em produção (ENV=production). "
        "Defina uma chave forte e única na variável de ambiente SECRET_KEY.",
        stacklevel=1,
    )

app = FastAPI(title="EDUSCANNER")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=ENV == "production",
)

# CORS desativado por padrão (mais seguro): o EDUSCANNER é servido e
# consumido pelo mesmo navegador/origem. Só habilite origens externas
# explicitamente via ALLOWED_ORIGINS se algo fora do próprio site
# precisar chamar a API (Seção 24).
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend/static"), name="static")

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(classes_router)
app.include_router(cards_router)
app.include_router(scanner_router)
app.include_router(reports_router)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return RedirectResponse("/dashboard", status_code=303)
