from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from datetime import datetime
from db import keys_col, users_col, requests_col
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


@router.post("/add_request")
def add_request(payload: dict = Body(default={})):
    try:
        requester = payload.get("requester_username")
        owner     = payload.get("owner_username")
        image_id  = payload.get("image_id")
        desc      = payload.get("image_description", "")
        token     = payload.get("token")

        if not requester or not token or not verify_token(requester, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        existing = requests_col.find_one({"image_id": image_id, "requester_username": requester})
        if existing:
            return {"message": "Demande déjà envoyée.", "status": existing["status"]}

        requests_col.insert_one({
            "image_id":           image_id,
            "image_description":  desc,
            "requester_username": requester,
            "owner_username":     owner,
            "date":               datetime.utcnow().isoformat(),
            "status":             "pending",
        })
        return {"message": "Demande envoyée."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_requests")
def get_requests(payload: dict = Body(default={})):
    try:
        owner = payload.get("owner_username")
        token = payload.get("token")

        if not owner or not token or not verify_token(owner, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        reqs = list(requests_col.find({"owner_username": owner}, {"_id": 0}))
        return {"requests": reqs}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grant_request")
def grant_request(payload: dict = Body(default={})):
    try:
        owner     = payload.get("owner_username")
        token     = payload.get("token")
        image_id  = payload.get("image_id")
        requester = payload.get("requester_username")

        if not owner or not token or not verify_token(owner, token):
            raise HTTPException(status_code=403, detail="Token invalide ou expiré.")

        key_data = keys_col.find_one({"image_id": image_id})
        if not key_data or key_data["owner_username"] != owner:
            raise HTTPException(status_code=403, detail="Action non autorisée.")

        keys_col.update_one(
            {"image_id": image_id},
            {"$addToSet": {"autorisations": requester}}
        )
        requests_col.update_one(
            {"image_id": image_id, "requester_username": requester},
            {"$set": {"status": "granted"}}
        )
        return {"message": "Accès accordé.", "image_id": image_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))