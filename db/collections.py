from pymongo import errors
from db.client import get_client

def init_collections():
    client = get_client()
    db = client["tiers-de-confiance"]

    try:
        existing = db.list_collection_names()
        for col_name in ["keys", "tokens", "users", "posts", "requests", "history"]:
            if col_name not in existing:
                db.create_collection(col_name)
                print(f"[OK] Collection '{col_name}' créée.")

        print("[OK] Accès aux collections réussi.")
        return {
            "users":    db["users"],
            "posts":    db["posts"],
            "keys":     db["keys"],
            "tokens":   db["tokens"],
            "requests": db["requests"],
            "history":  db["history"],
        }
    except errors.PyMongoError as e:
        print(f"[ERREUR] Problème collections : {e}")
        exit(1)