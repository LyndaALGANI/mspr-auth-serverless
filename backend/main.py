from fastapi import FastAPI

from utils.password import generate_password
from utils.qr import generate_qr
from utils.crypto import encrypt
from utils.twofa import generate_2fa

app = FastAPI()
@app.get("/")
def home():
    return {"message": "API MSPR fonctionne"}
@app.post("/create-user")
def create_user(username: str):

    password = generate_password()

    generate_qr(password, "password_qr.png")

    secret, uri = generate_2fa(username)
    generate_qr(uri, "2fa_qr.png")

    encrypted_password = encrypt(password)

    return {
        "username": username,
        "password_qr": "password_qr.png",
        "2fa_qr": "2fa_qr.png",
        "message": "Utilisateur créé"
    }