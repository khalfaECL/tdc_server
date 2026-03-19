from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64


def encrypt_image(image_bytes: bytes, key_base64: str) -> str:
    key = base64.b64decode(key_base64)
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(iv, image_bytes, None)
    result = iv + encrypted
    return base64.b64encode(result).decode()

def decrypt_image(encrypted_base64: str, key_base64: str) -> bytes:
    key = base64.b64decode(key_base64)
    data = base64.b64decode(encrypted_base64)
    iv = data[:12]
    encrypted = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, encrypted, None)