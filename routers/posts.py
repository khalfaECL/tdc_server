from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from typing import Optional
from datetime import datetime
import base64
import os
import uuid

from db import keys_col, posts_col, users_col, history_col
from core.security import verify_token
from services.crypto import encrypt_image, decrypt_image

router = APIRouter()


@router.post("/add_post")
async def add_post(
    user_id: str = Form(...),
    owner_username: str = Form(...),
    token: str = Form(...),
    caption: str = Form(default=""),
    image: UploadFile = File(...),
    authorized_users: str = Form(default=""),
    ephemeral_duration: int = Form(default=5),
    max_views: int = Form(default=3),
    view_cooldown: int = Form(default=10),
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
            "image_id":          image_id,
            "user_id":           user_id,
            "owner_username":    owner_username,
            "key":               generated_key,
            "valid":             True,
            "autorisations":     authorized_list,
            "ephemeral_duration": ephemeral_duration,
            "max_views":         max_views,
            "view_cooldown":     view_cooldown,
            "created_at":        datetime.utcnow()
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


@router.delete("/delete_post/{image_id}")
async def delete_post(image_id: str, payload: dict = Body(default={})):
    try:
        username = payload.get("username")
        token    = payload.get("token")

        if not username or not token or not verify_token(username, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data:
            raise HTTPException(status_code=404, detail="Post non trouvé.")

        if key_data.get("owner_username") != username:
            raise HTTPException(status_code=403, detail="Action non autorisée.")

        posts_col.delete_one({"image_id": image_id})
        keys_col.delete_one({"image_id": image_id})

        return {"message": "Post supprimé avec succès.", "image_id": image_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/my_posts")
def my_posts(payload: dict = Body(default={})):
    try:
        username = payload.get("username")
        token    = payload.get("token")

        if not username or not token or not verify_token(username, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        keys = list(keys_col.find({"owner_username": username, "valid": True}, {"_id": 0}))
        photos = []
        for k in keys:
            post = posts_col.find_one({"image_id": k["image_id"]}, {"image": 0, "_id": 0})
            if post:
                created_at = k.get("created_at")
                photos.append({
                    "image_id":          k["image_id"],
                    "description":       post.get("caption", ""),
                    "date_creation":     created_at.isoformat() if created_at else "",
                    "preview_uri":       None,
                    "authorized":        k.get("autorisations", []),
                    "access_count":      0,
                    "blocked":           k.get("blocked", False),
                    "history":           [],
                    "ephemeralDuration": k.get("ephemeral_duration", 5),
                    "maxViews":          k.get("max_views", 3),
                    "view_cooldown":     k.get("view_cooldown", 10),
                })
        photos.sort(key=lambda x: x.get("date_creation", ""), reverse=True)
        return {"photos": photos}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feed")
def get_feed(payload: dict = Body(default={})):
    try:
        username = payload.get("username")
        token    = payload.get("token")

        if not username or not token or not verify_token(username, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        keys = list(keys_col.find({"valid": True}, {"_id": 0}))
        feed = []
        for k in keys:
            post = posts_col.find_one({"image_id": k["image_id"]}, {"image": 0, "_id": 0})
            if post:
                created_at = k.get("created_at")
                feed.append({
                    "image_id":          k["image_id"],
                    "owner_username":    k["owner_username"],
                    "description":       post.get("caption", ""),
                    "caption":           post.get("caption", ""),
                    "authorized":        k.get("autorisations", []),
                    "date_creation":     created_at.isoformat() if created_at else "",
                    "preview_uri":       None,
                    "ephemeralDuration": k.get("ephemeral_duration", 5),
                    "maxViews":          k.get("max_views", 3),
                    "view_cooldown":     k.get("view_cooldown", 10),
                })
        feed.sort(key=lambda x: x.get("date_creation", ""), reverse=True)
        return {"posts": feed}

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
            # Enforce max_views and cooldown for non-owners
            if not is_owner:
                max_views = key_data.get("max_views", 3)
                view_count = history_col.count_documents({
                    "image_id": image_id,
                    "viewer_username": username
                })
                print(f"[DEBUG] viewer={username} image={image_id} view_count={view_count} max_views={max_views}")
                if view_count >= max_views:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Nombre maximum de visualisations atteint ({max_views})."
                    )

                cooldown_min = int(key_data.get("view_cooldown", 10))
                print(f"[DEBUG] cooldown_min={cooldown_min}")
                if cooldown_min > 0:
                    last = history_col.find_one(
                        {"image_id": image_id, "viewer_username": username},
                        sort=[("accessed_at", -1)]
                    )
                    if last:
                        last_time = datetime.fromisoformat(last["accessed_at"])
                        elapsed = (datetime.utcnow() - last_time).total_seconds() / 60
                        if elapsed < cooldown_min:
                            remain = max(1, round(cooldown_min - elapsed))
                            raise HTTPException(
                                status_code=429,
                                detail=f"Délai non respecté. Réessayez dans {remain} minute(s)."
                            )

            decrypted_bytes = decrypt_image(post["image"], key_data["key"])

            # Record access server-side (ensures cooldown is enforced on next request)
            if not is_owner:
                history_col.insert_one({
                    "image_id":          image_id,
                    "image_description": post.get("caption", ""),
                    "viewer_username":   username,
                    "owner_username":    key_data.get("owner_username", ""),
                    "accessed_at":       datetime.utcnow().isoformat(),
                    "type":              "app",
                })

            return {
                "image_id":           image_id,
                "caption":            post["caption"],
                "image":              base64.b64encode(decrypted_bytes).decode(),
                "decrypted":          True,
                "ephemeral_duration": key_data.get("ephemeral_duration", 5),
                "max_views":          key_data.get("max_views", 3),
            }
        else:
            return {
                "image_id":  image_id,
                "caption":   post["caption"],
                "image":     post["image"],
                "decrypted": False
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log_access")
def log_access(payload: dict = Body(default={})):
    try:
        viewer    = payload.get("viewer_username")
        owner     = payload.get("owner_username")
        image_id  = payload.get("image_id")
        desc      = payload.get("image_description", "")
        token     = payload.get("token")
        acc_type  = payload.get("type", "app")

        if not viewer or not token or not verify_token(viewer, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        history_col.insert_one({
            "image_id":          image_id,
            "image_description": desc,
            "viewer_username":   viewer,
            "owner_username":    owner,
            "accessed_at":       datetime.utcnow().isoformat(),
            "type":              acc_type,
        })
        return {"message": "Accès enregistré."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_history")
def get_history(payload: dict = Body(default={})):
    """History of accesses to images owned by username."""
    try:
        owner = payload.get("owner_username")
        token = payload.get("token")

        if not owner or not token or not verify_token(owner, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        entries = list(history_col.find({"owner_username": owner}, {"_id": 0}))
        entries.sort(key=lambda x: x.get("accessed_at", ""), reverse=True)
        return {"accesses": entries}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_my_accesses")
def get_my_accesses(payload: dict = Body(default={})):
    """History of images accessed by username."""
    try:
        viewer = payload.get("viewer_username")
        token  = payload.get("token")

        if not viewer or not token or not verify_token(viewer, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        entries = list(history_col.find({"viewer_username": viewer}, {"_id": 0}))
        entries.sort(key=lambda x: x.get("accessed_at", ""), reverse=True)
        return {"accesses": entries}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))