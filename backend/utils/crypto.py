import os
from cryptography.fernet import Fernet

# Fichier où la clé est sauvegardée
KEY_FILE = os.path.join(os.path.dirname(__file__), "secret.key")

def _charger_cle():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read().strip()
    # Première fois : on génère et on sauvegarde
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
