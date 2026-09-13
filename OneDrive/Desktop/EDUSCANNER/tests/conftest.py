"""
Fixtures compartilhadas pelos testes.

Cada teste roda contra um banco SQLite isolado (arquivo temporário),
recriado do zero antes de cada teste — para que testes de
autenticação, turmas e cartões não interfiram uns nos outros nem no
banco de desenvolvimento (data/eduscanner.db).
"""

import os
import tempfile
from pathlib import Path

# IMPORTANTE: isto precisa rodar antes de qualquer `import backend...`
# em qualquer módulo de teste, porque backend/db.py lê DATABASE_URL no
# momento da importação. O conftest.py é sempre carregado pelo pytest
# antes dos arquivos de teste do mesmo diretório, então este bloco no
# nível do módulo garante a ordem certa.
_tmp_dir = tempfile.mkdtemp(prefix="eduscanner_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp_dir) / 'test.db'}"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi.testclient import TestClient

from backend.db import Base, engine
import backend.models  # noqa: F401  garante que os modelos estão registrados
from backend.main import app


@pytest.fixture()
def client():
    """Cliente de teste com um banco limpo a cada teste."""
    from backend.rate_limit import login_limiter, scanner_limiter

    # O TestClient sempre "conecta" do mesmo IP fake, então os
    # limitadores (globais, em memória) precisam ser zerados a cada
    # teste — senão testes não relacionados a rate limiting acabam
    # esbarrando no limite acumulado por testes anteriores.
    login_limiter._hits.clear()
    scanner_limiter._hits.clear()

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def register_and_login(client, name="Prof Ana", email="ana@escola.com", password="senha123"):
    """Atalho usado por vários testes: cria um professor e já deixa a
    sessão logada (o próprio /register já loga automaticamente)."""
    client.post("/register", data={"name": name, "email": email, "password": password})
    return email, password


def login(client, email="ana@escola.com", password="senha123"):
    """Loga um professor que já existe (diferente de register_and_login,
    que sempre tenta CRIAR a conta)."""
    client.post("/login", data={"email": email, "password": password})
    return email, password
