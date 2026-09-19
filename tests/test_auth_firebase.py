import os
os.environ.setdefault('DATABASE_URL', 'sqlite:///./test_eduscanner_auth.db')
os.environ.setdefault('COOKIE_SECURE', 'false')

from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import AllowedGoogleEmail, Usuario
import app.main as main_module

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _fake_google(email):
    return {
        'uid': 'firebase-test-uid',
        'email': email,
        'email_verified': True,
        'name': 'Professor Teste',
        'firebase': {'sign_in_provider': 'google.com'},
    }


def test_google_email_permitido_cria_usuario_e_sessao(monkeypatch):
    db = SessionLocal()
    db.add(AllowedGoogleEmail(email='professor@escola.edu.br'))
    db.commit(); db.close()
    monkeypatch.setattr(main_module, 'verify_firebase_token', lambda token: _fake_google('  PROFESSOR@ESCOLA.EDU.BR  '))

    response = client.post('/api/auth/firebase', json={'id_token': 'ok'})
    assert response.status_code == 200
    assert response.json()['tipo'] == 'professor'
    assert 'eduscanner_session' in response.cookies

    db = SessionLocal()
    user = db.query(Usuario).filter(Usuario.login == 'professor@escola.edu.br').first()
    assert user is not None
    db.close()


def test_google_email_negado_retorna_mensagem_da_regra(monkeypatch):
    monkeypatch.setattr(main_module, 'verify_firebase_token', lambda token: _fake_google('NAO.AUTORIZADO@ESCOLA.EDU.BR'))
    response = client.post('/api/auth/firebase', json={'id_token': 'nope'})
    assert response.status_code == 403
    assert response.json()['detail'] == 'Seu e-mail ainda não foi autorizado pelo administrador. Solicite a liberação do seu acesso.'
    assert 'eduscanner_session' not in response.cookies
