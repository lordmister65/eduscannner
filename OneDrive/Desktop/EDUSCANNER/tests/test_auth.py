"""
Testes de autenticação (Seção 6 e 32).
"""

from tests.conftest import register_and_login


def test_register_creates_account_and_logs_in(client):
    r = client.post("/register", data={"name": "Prof Ana", "email": "ana@escola.com", "password": "senha123"})
    assert r.status_code == 200
    assert r.url.path == "/dashboard"


def test_register_rejects_duplicate_email(client):
    register_and_login(client)
    r = client.post("/register", data={"name": "Outra Ana", "email": "ana@escola.com", "password": "outrasenha"})
    assert r.status_code == 200
    assert "já está cadastrado" in r.text


def test_password_is_never_stored_in_plain_text(client):
    """Seção 6: nunca armazenar senhas em texto puro."""
    register_and_login(client, password="minhaSenhaSecreta")
    from backend.db import SessionLocal
    from backend.models import User

    db = SessionLocal()
    user = db.query(User).filter_by(email="ana@escola.com").first()
    assert user is not None
    assert user.password_hash != "minhaSenhaSecreta"
    assert user.password_hash.startswith("$2b$")  # hash bcrypt
    db.close()


def test_login_with_correct_password_succeeds(client):
    email, password = register_and_login(client)
    client.get("/logout")
    r = client.post("/login", data={"email": email, "password": password})
    assert r.status_code == 200
    assert r.url.path == "/dashboard"


def test_login_with_wrong_password_fails(client):
    email, _ = register_and_login(client)
    client.get("/logout")
    r = client.post("/login", data={"email": email, "password": "senhaerrada"})
    assert r.status_code == 200
    assert r.url.path != "/dashboard"
    assert "inválid" in r.text.lower()


def test_login_with_unknown_email_fails(client):
    r = client.post("/login", data={"email": "ninguem@escola.com", "password": "qualquer"})
    assert "inválid" in r.text.lower()


def test_logout_clears_session(client):
    register_and_login(client)
    client.get("/logout")
    r = client.get("/dashboard")
    assert r.url.path == "/login"


def test_protected_routes_require_login(client):
    for path in ("/dashboard", "/turmas", "/cartoes", "/scanner", "/relatorios"):
        r = client.get(path)
        assert r.url.path == "/login", f"{path} deveria exigir login"
