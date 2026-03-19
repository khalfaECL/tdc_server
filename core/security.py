from hashlib import sha256
from datetime import datetime
from db import users_col, tokens_col


def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def get_user(username: str):
    return users_col.find_one({"username": username})

def verify_token(username: str, token: str) -> bool:
    session = tokens_col.find_one({"username": username, "token": token})
    if not session:
        return False
    if session["expires_at"] < datetime.utcnow():
        tokens_col.delete_one({"token": token})
        return False
    return True