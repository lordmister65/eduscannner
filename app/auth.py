import base64, hashlib, hmac, json, os, time
from functools import lru_cache

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario

SECRET_KEY = os.getenv('SECRET_KEY', 'troque-esta-chave-no-render')
COOKIE_NAME = 'eduscanner_session'
SESSION_SECONDS = 60 * 60 * 12


def make_token(user_id: int) -> str:
    exp = int(time.time()) + SESSION_SECONDS
    body = f'{user_id}.{exp}'
    sig = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f'{body}.{sig}'


def read_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        uid, exp, sig = token.split('.', 2)
        body = f'{uid}.{exp}'
        expected = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected) or int(exp) < time.time():
            return None
        return int(uid)
    except Exception:
        return None


def set_login_cookie(response: Response, user_id: int):
    secure = os.getenv('COOKIE_SECURE', 'true').strip().lower() not in ('0', 'false', 'no')
    response.set_cookie(COOKIE_NAME, make_token(user_id), max_age=SESSION_SECONDS,
                        httponly=True, secure=secure, samesite='lax', path='/')


def clear_login_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, path='/')


def _service_account_info() -> dict:
    raw = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON', '').strip()
    if raw:
        try:
            if raw.startswith('{'):
                return json.loads(raw)
            return json.loads(base64.b64decode(raw).decode('utf-8'))
        except Exception as exc:
            raise RuntimeError('FIREBASE_SERVICE_ACCOUNT_JSON inválido.') from exc

    private_key = os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n').strip()
    info = {
        'type': 'service_account',
        'project_id': os.getenv('FIREBASE_PROJECT_ID', '').strip(),
        'private_key_id': os.getenv('FIREBASE_PRIVATE_KEY_ID', '').strip(),
        'private_key': private_key,
        'client_email': os.getenv('FIREBASE_CLIENT_EMAIL', '').strip(),
        'client_id': os.getenv('FIREBASE_CLIENT_ID', '').strip(),
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
        'client_x509_cert_url': os.getenv('FIREBASE_CLIENT_CERT_URL', '').strip(),
    }
    if not info['project_id'] or not info['private_key'] or not info['client_email']:
        raise RuntimeError('Credenciais do Firebase Admin não configuradas.')
    return info


@lru_cache(maxsize=1)
def get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        info = _service_account_info()
        return firebase_admin.initialize_app(credentials.Certificate(info), {'projectId': info['project_id']})


def verify_firebase_token(id_token: str) -> dict:
    try:
        return firebase_auth.verify_id_token(id_token, app=get_firebase_app(), check_revoked=True)
    except Exception as exc:
        raise HTTPException(401, 'Token do Firebase inválido ou expirado.') from exc


def ensure_firebase_user(email: str, password: str | None = None, display_name: str | None = None):
    """Cria/atualiza a conta de e-mail/senha usada pelo login tradicional."""
    email = email.strip().lower()
    app = get_firebase_app()
    try:
        user = firebase_auth.get_user_by_email(email, app=app)
        changes = {}
        if password:
            changes['password'] = password
        if display_name:
            changes['display_name'] = display_name
        if changes:
            firebase_auth.update_user(user.uid, app=app, **changes)
        return user
    except firebase_auth.UserNotFoundError:
        if not password:
            return None
        return firebase_auth.create_user(email=email, password=password, display_name=display_name, app=app)


def delete_firebase_user_by_email(email: str):
    try:
        user = firebase_auth.get_user_by_email(email.strip().lower(), app=get_firebase_app())
        firebase_auth.delete_user(user.uid, app=get_firebase_app())
    except firebase_auth.UserNotFoundError:
        pass


def current_user(eduscanner_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> Usuario:
    uid = read_token(eduscanner_session)
    user = db.get(Usuario, uid) if uid else None
    if not user or not user.ativo:
        raise HTTPException(401, 'Faça login para continuar.')
    return user


def admin_user(user: Usuario = Depends(current_user)) -> Usuario:
    if user.tipo != 'admin':
        raise HTTPException(403, 'Acesso exclusivo do administrador.')
    return user


def can_access_turma(user: Usuario, turma_id: int) -> bool:
    return user.tipo == 'admin' or any(t.id == turma_id for t in user.turmas)
