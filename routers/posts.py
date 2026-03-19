from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from typing import Optional
from datetime import datetime
import base64
import os
import uuid

from db import keys_col, posts_col, users_col
from core.security import verify_token
from services.crypto import encrypt_image, decrypt_image

router = APIRouter()


@router.post("/add_post")
async def add_post(
    user_id: str = Form(...),
    owner_username: str = Form(...),
    token: str = Form(...),
    caption: str = Form(...),
    image: UploadFile = File(...),
    authorized_users: str = Form(default="")
):
    try:
        if not verify_token(owner_username, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        authorized_list = (
            [] if authorized_users.strip() == ""
            else [u.strip() for u in authorized_users.split(",") if u.strip()]
        )

        invalid_users = [u for u in authorized_list if not users_col.find_one({"username": u})]
        if invalid_users:
            raise HTTPException(status_code=404, detail=f"Utilisateurs introuvables : {invalid_users}")

        content = await image.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image trop lourde (max 10MB).")

        image_id = str(uuid.uuid4())
        generated_key = base64.b64encode(os.urandom(32)).decode()
        encrypted_image = encrypt_image(content, generated_key)

        posts_col.insert_one({
            "image_id": image_id,
            "user_id": user_id,
            "caption": caption,
            "image": encrypted_image
        })

        keys_col.insert_one({
            "image_id": image_id,
            "user_id": user_id,
            "owner_username": owner_username,
            "key": generated_key,
            "valid": True,
            "autorisations": authorized_list,
            "created_at": datetime.utcnow()
        })

        return {
            "message": "Publication ajoutée avec succès.",
            "image_id": image_id,
            "autorisations": authorized_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts/{image_id}")
def get_post(image_id: str, payload: dict = Body(default={})):
    try:
        username = payload.get("username")
        token = payload.get("token")

        post = posts_col.find_one({"image_id": image_id})
        if not post:
            raise HTTPException(status_code=404, detail="Post non trouvé.")

        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data:
            raise HTTPException(status_code=404, detail="Clé non trouvée.")

        is_owner = username == key_data["owner_username"]
        is_authorized = username in key_data.get("autorisations", [])
        has_valid_token = username and token and verify_token(username, token)

        if has_valid_token and (is_owner or is_authorized):
            decrypted_bytes = decrypt_image(post["image"], key_data["key"])
            return {
                "image_id": image_id,
                "caption": post["caption"],
                "image": base64.b64encode(decrypted_bytes).decode(),
                "decrypted": True
            }
        else:
            return {
                "image_id": image_id,
                "caption": post["caption"],
                "image": post["image"],
                "decrypted": False
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))