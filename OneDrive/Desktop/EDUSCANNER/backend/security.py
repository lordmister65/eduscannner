from passlib.context import CryptContext
from backend.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    return pwd.hash(password)

def verify_password(password, password_hash):
    return pwd.verify(password, password_hash)

def get_current_user(request, db):
    uid = request.session.get("user_id")
    return db.get(User, uid) if uid else None
