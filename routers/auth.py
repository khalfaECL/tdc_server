from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import users_col, tokens_col, posts_col, keys_col, requests_col, history_col
from core.security import hash_password, verify_password, get_user
from secrets import token_hex
from datetime import datetime, timedelta
import uuid

router = APIRouter()

class UserIn(BaseModel):
    username: str
    password: str


def validate_password(password: str):
    import re
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères.")
    if not re.search(r'[A-Z]', password):
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins une majuscule.")
    if not re.search(r'[0-9]', password):
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins un chiffre.")
    if not re.search(r'[^A-Za-z0-9]', password):
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins un caractère spécial.")

@router.post("/register")
def register(user: UserIn):
    if len(user.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="L'identifiant doit contenir au moins 3 caractères.")
    if ' ' in user.username:
        raise HTTPException(status_code=400, detail="L'identifiant ne peut pas contenir d'espaces.")
    validate_password(user.password)
    if get_user(user.username):
        raise HTTPException(status_code=400, detail="Cet identifiant est déjà utilisé.")

    user_id = str(uuid.uuid4())

    users_col.insert_one({
        "user_id": user_id,
        "username": user.username,
        "password": hash_password(user.password),
        "created_at": datetime.utcnow()
    })

    return {
        "message": "Inscription réussie",
        "user_id": user_id
    }


@router.post("/login")
def login(user: UserIn):
    db_user = get_user(user.username)
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    token = token_hex(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    tokens_col.insert_one({
        "user_id": db_user["user_id"],
        "username": db_user["username"],
        "token": token,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at
    })

    return {
        "message": "Connexion réussie",
        "user_id": db_user["user_id"],
        "username": db_user["username"],
        "token": token,
        "expires_at": expires_at.isoformat()
    }


@router.post("/logout")
def logout(payload: dict):
    token = payload.get("token")
    result = tokens_col.delete_one({"token": token})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Token introuvable.")
    return {"message": "Déconnexion réussie."}


@router.delete("/delete_account")
def delete_account(payload: dict):
    username = payload.get("username")
    token    = payload.get("token")

    if not username or not token or not verify_token(username, token):
        raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    # Récupérer les image_ids du user pour nettoyer posts + keys
    image_ids = [k["image_id"] for k in keys_col.find({"owner_username": username}, {"image_id": 1})]

    posts_col.delete_many({"image_id": {"$in": image_ids}})
    keys_col.delete_many({"owner_username": username})
    history_col.delete_many({"owner_username": username})
    requests_col.delete_many({"$or": [{"owner_username": username}, {"requester_username": username}]})
    tokens_col.delete_many({"username": username})
    users_col.delete_one({"username": username})

    return {"message": "Compte et données supprimés."}