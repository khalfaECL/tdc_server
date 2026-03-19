from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from db import keys_col, users_col
from core.security import verify_token

router = APIRouter()

# ---- Modèles ----
class AuthorizePayload(BaseModel):
    owner_username: str
    token: str
    authorized_users: list[str]

class RevokePayload(BaseModel):
    owner_username: str
    token: str


@router.post("/authorize/{image_id}")
def authorize_users(image_id: str, payload: AuthorizePayload):
    try:
        if not verify_token(payload.owner_username, payload.token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data:
            raise HTTPException(status_code=404, detail="Image non trouvée.")

        if key_data["owner_username"] != payload.owner_username:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas le propriétaire.")

        invalid_users = [u for u in payload.authorized_users if not users_col.find_one({"username": u})]
        if invalid_users:
            raise HTTPException(status_code=404, detail=f"Utilisateurs introuvables : {invalid_users}")

        keys_col.update_one(
            {"image_id": image_id},
            {"$addToSet": {"autorisations": {"$each": payload.authorized_users}}}
        )

        updated = keys_col.find_one({"image_id": image_id})
        return {
            "message": "Accès accordé.",
            "image_id": image_id,
            "autorisations": updated.get("autorisations", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/revoke/{image_id}/{target_username}")
def revoke_access(image_id: str, target_username: str, payload: RevokePayload = Body(...)):
    try:
        if not verify_token(payload.owner_username, payload.token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data:
            raise HTTPException(status_code=404, detail="Image non trouvée.")

        if key_data["owner_username"] != payload.owner_username:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas le propriétaire.")

        if target_username not in key_data.get("autorisations", []):
            raise HTTPException(status_code=404, detail=f"{target_username} n'est pas dans les autorisations.")

        keys_col.update_one(
            {"image_id": image_id},
            {"$pull": {"autorisations": target_username}}
        )

        updated = keys_col.find_one({"image_id": image_id})
        return {
            "message": f"Accès révoqué pour {target_username}.",
            "image_id": image_id,
            "autorisations": updated.get("autorisations", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))