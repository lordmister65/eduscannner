import base64, hashlib, hmac, os, secrets, time
from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from .database import get_db
from .models import Usuario

SECRET_KEY = os.getenv('SECRET_KEY', 'troque-esta-chave-no-render')
COOKIE_NAME = 'eduscanner_session'
SESSION_SECONDS = 60 * 60 * 12

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210_000)
    return 'pbkdf2_sha256$210000$%s$%s' % (base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode())

def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_b64, digest_b64 = stored.split('$', 3)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def make_token(user_id: int) -> str:
    exp = int(time.time()) + SESSION_SECONDS
    body = f'{user_id}.{exp}'
    sig = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f'{body}.{sig}'

def read_token(token: str | None) -> int | None:
    if not token: return None
    try:
        uid, exp, sig = token.split('.', 2)
        body = f'{uid}.{exp}'
        expected = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected) or int(exp) < time.time(): return None
        return int(uid)
    except Exception:
        return None

def set_login_cookie(response: Response, user_id: int):
    response.set_cookie(COOKIE_NAME, make_token(user_id), max_age=SESSION_SECONDS, httponly=True, secure=True, samesite='lax', path='/')

def clear_login_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, path='/')

def current_user(eduscanner_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> Usuario:
    uid = read_token(eduscanner_session)
    user = db.get(Usuario, uid) if uid else None
    if not user or not user.ativo: raise HTTPException(401, 'Faça login para continuar.')
    return user

def admin_user(user: Usuario = Depends(current_user)) -> Usuario:
    if user.tipo != 'admin': raise HTTPException(403, 'Acesso exclusivo do administrador.')
    return user

def can_access_turma(user: Usuario, turma_id: int) -> bool:
    return user.tipo == 'admin' or any(t.id == turma_id for t in user.turmas)
