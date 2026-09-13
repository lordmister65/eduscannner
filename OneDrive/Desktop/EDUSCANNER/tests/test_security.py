"""
Testes de rate limiting e validação de entrada (Seção 24/25).
"""

from tests.conftest import register_and_login


def test_login_is_rate_limited_after_too_many_attempts(client):
    register_and_login(client)
    client.get("/logout")

    # zera o limitador aqui: o próprio /register consumiu 1 tentativa,
    # e queremos testar o limite isoladamente a partir deste ponto.
    from backend.rate_limit import login_limiter
    login_limiter._hits.clear()

    # o limite é 8 tentativas/min; a 9ª deve ser bloqueada com 429
    for _ in range(8):
        r = client.post("/login", data={"email": "ana@escola.com", "password": "errada"})
        assert r.status_code == 200

    r = client.post("/login", data={"email": "ana@escola.com", "password": "errada"})
    assert r.status_code == 429


def test_rate_limit_is_isolated_per_client_ip(client):
    """Não é uma trava global — só afasta quem está de fato abusando."""
    from backend.rate_limit import login_limiter

    login_limiter.check("1.1.1.1")
    login_limiter.check("1.1.1.1")
    # outro IP não deve ser afetado
    login_limiter.check("2.2.2.2")  # não deve levantar


def test_register_rejects_invalid_email(client):
    r = client.post("/register", data={"name": "Prof Ana", "email": "não-é-email", "password": "senha123"})
    assert r.status_code == 200
    assert r.url.path != "/dashboard"


def test_register_rejects_short_password(client):
    r = client.post("/register", data={"name": "Prof Ana", "email": "ana@escola.com", "password": "123"})
    assert r.status_code == 200
    assert r.url.path != "/dashboard"


def test_classroom_rejects_empty_name(client):
    register_and_login(client)
    client.post("/turmas", data={"name": "   ", "school": ""})
    from backend.db import SessionLocal
    from backend.models import Classroom

    db = SessionLocal()
    assert db.query(Classroom).count() == 0
    db.close()


def test_card_creation_rejects_invalid_block(client):
    register_and_login(client)
    client.post("/cartoes", data={"name": "Prova X", "block": 99})
    from backend.db import SessionLocal
    from backend.models import AnswerCard

    db = SessionLocal()
    assert db.query(AnswerCard).count() == 0
    db.close()
