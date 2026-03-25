from pymongo import MongoClient, errors
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

def get_client() -> MongoClient:
    try:
        print("[INFO] Connexion à MongoDB...")
        client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
        print("[OK] Connexion établie.")
        return client
    except errors.ConnectionFailure as e:
        print(f"[ERREUR] Échec de connexion : {e}")
        exit(1)