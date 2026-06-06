import os
from cryptography.fernet import Fernet

DATA_DIR = os.getenv("DATA_DIR", "/tmp/mspr-data")
KEY_DIR = os.path.join(DATA_DIR, "keys")
os.makedirs(KEY_DIR, exist_ok=True)

KEY_FILE = os.path.join(KEY_DIR, "secret.key")

def _charger_cle():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read().strip()

    cle = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(cle)
    return cle

cle = _charger_cle()
cipher = Fernet(cle)

def encrypt(data: str) -> bytes:
    return cipher.encrypt(data.encode())

def decrypt(data: str) -> str:
    return cipher.decrypt(data.encode()).decode()