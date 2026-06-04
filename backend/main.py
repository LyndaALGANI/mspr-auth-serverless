# from fastapi import FastAPI
# from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware

# from database import cursor, conn
# from datetime import datetime

# from utils.crypto import encrypt, decrypt
# from utils.password import generate_password
# from utils.qr import generate_qr
# from utils.twofa import generate_2fa, verify_2fa

# app = FastAPI()

# #  CORS (important pour frontend)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# #  accès aux QR
# app.mount("/static", StaticFiles(directory="."), name="static")


# #  TEST
# @app.get("/")
# def home():
#     return {"message": "API OK"}


# # =========================
# #  INSCRIPTION
# # =========================

# #  CREATE USER
# @app.post("/create-user")
# def create_user(username: str):

#     cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
#     if cursor.fetchone():
#         return {"error": "Utilisateur déjà existant"}

#     password = generate_password()

#     # QR PASSWORD
#     password_file = f"{username}_password.png"
#     generate_qr(password, password_file)

#     encrypted_password = encrypt(password)

#     gendate = datetime.now().strftime("%Y-%m-%d")

#     cursor.execute(
#         "INSERT INTO Users (username, password, MFA, gendate, expired) VALUES (?, ?, ?, ?, ?)",
#         (username, encrypted_password.decode(), "", gendate, 0)
#     )
#     conn.commit()

#     return {
#         "password_qr": f"http://127.0.0.1:8000/static/{password_file}"
#     }


# #  VALIDATION PASSWORD → QR 2FA
# @app.post("/register-step2")
# def register_step2(username: str, password: str):

#     cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
#     user = cursor.fetchone()

#     if not user:
#         return {"error": "Utilisateur introuvable"}

#     stored_password = user[2]
#     decrypted_password = decrypt(stored_password)

#     if password != decrypted_password:
#         return {"error": "Mot de passe incorrect"}

#     #  DEBUG
#     print("PASSWORD OK")

#     # 2FA
#     secret, uri = generate_2fa(username)

#     print("SECRET:", secret)
#     print("URI:", uri)

#     filename = f"{username}_2fa.png"
#     generate_qr(uri, filename)

#     print("QR GENERATED:", filename)

#     cursor.execute(
#         "UPDATE Users SET MFA = ? WHERE username = ?",
#         (secret, username)
#     )
#     conn.commit()

#     return {
#         "2fa_qr": f"http://127.0.0.1:8000/static/{filename}"
#     }
# #  VALIDATION 2FA (ACTIVATION)
# @app.post("/register-step3")
# def register_step3(username: str, code: str):

#     cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
#     user = cursor.fetchone()

#     if not user:
#         return {"error": "Utilisateur introuvable"}

#     secret = user[3]

#     if not verify_2fa(secret, code):
#         return {"error": "Code invalide"}

#     return {"message": "Compte activé"}


# # =========================
# #  CONNEXION
# # =========================

# #  LOGIN STEP 1
# @app.post("/login-step1")
# def login_step1(username: str, password: str):

#     cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
#     user = cursor.fetchone()

#     if not user:
#         return {"error": "Utilisateur introuvable"}

#     stored_password = user[2]
#     secret = user[3]

#     decrypted_password = decrypt(stored_password)

#     if password != decrypted_password:
#         return {"error": "Mot de passe incorrect"}

#     import pyotp
#     uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="MSPR")

#     file = f"{username}_login_2fa.png"
#     generate_qr(uri, file)

#     return {
#         "2fa_qr": f"http://127.0.0.1:8000/static/{file}"
#     }


# #  LOGIN STEP 2
# @app.post("/login-step2")
# def login_step2(username: str, code: str):

#     cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
#     user = cursor.fetchone()

#     if not user:
#         return {"error": "Utilisateur introuvable"}

#     secret = user[3]

#     if not verify_2fa(secret, code):
#         return {"error": "Code invalide"}

#     return {"message": "Connexion réussie"}




from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from database import cursor, conn
from datetime import datetime

from utils.crypto import encrypt, decrypt
from utils.password import generate_password
from utils.qr import generate_qr
from utils.twofa import generate_2fa, verify_2fa

app = FastAPI()

#  CORS (frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IMPORTANT : pointer vers le dossier qrcodes
app.mount("/static", StaticFiles(directory="qrcodes"), name="static")


# =========================
#  TEST
# =========================
@app.get("/")
def home():
    return {"message": "API OK"}


# =========================
# INSCRIPTION
# =========================

# CREATE USER → QR PASSWORD
@app.post("/create-user")
def create_user(username: str):

    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    if cursor.fetchone():
        return {"error": "Utilisateur déjà existant"}

    password = generate_password()

    # QR PASSWORD
    password_file = f"{username}_password.png"
    generate_qr(password, password_file)  # sera enregistré dans qrcodes/

    encrypted_password = encrypt(password)

    gendate = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "INSERT INTO Users (username, password, MFA, gendate, expired) VALUES (?, ?, ?, ?, ?)",
        (username, encrypted_password.decode(), "", gendate, 0)
    )
    conn.commit()
    print(f"Mot de passe généré pour {username} : {password}")

    return {
        "password_qr": f"http://127.0.0.1:8000/static/{password_file}"
    }


# VALIDATION PASSWORD → QR 2FA
@app.post("/register-step2")
def register_step2(username: str, password: str):

    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        return {"error": "Utilisateur introuvable"}

    stored_password = user[2]
    decrypted_password = decrypt(stored_password)

    if password != decrypted_password:
        return {"error": "Mot de passe incorrect"}

    #  Génération 2FA
    secret, uri = generate_2fa(username)

    filename = f"{username}_2fa.png"
    generate_qr(uri, filename)

    #  Sauvegarde secret
    cursor.execute(
        "UPDATE Users SET MFA = ? WHERE username = ?",
        (secret, username)
    )
    conn.commit()

    return {
        "2fa_qr": f"http://127.0.0.1:8000/static/{filename}"
    }


# VALIDATION 2FA (ACTIVATION)
@app.post("/register-step3")
def register_step3(username: str, code: str):

    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        return {"error": "Utilisateur introuvable"}

    secret = user[3]

    if not secret:
        return {"error": "2FA non initialisé"}

    if not verify_2fa(secret, code):
        return {"error": "Code invalide"}

    return {"message": "Compte activé"}


# =========================
# CONNEXION
# =========================

#  LOGIN STEP 1 → QR 2FA
@app.post("/login-step1")
def login_step1(username: str, password: str):

    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        return {"error": "Utilisateur introuvable"}

    stored_password = user[2]
    secret = user[3]

    decrypted_password = decrypt(stored_password)

    if password != decrypted_password:
        return {"error": "Mot de passe incorrect"}

    if not secret:
        return {"error": "2FA non configuré"}

    import pyotp
    uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="MSPR")

    filename = f"{username}_login_2fa.png"
    generate_qr(uri, filename)

    return {
        "2fa_qr": f"http://127.0.0.1:8000/static/{filename}"
    }


#  LOGIN STEP 2 → VALIDATION 2FA
@app.post("/login-step2")
def login_step2(username: str, code: str):

    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        return {"error": "Utilisateur introuvable"}

    secret = user[3]

    if not verify_2fa(secret, code):
        return {"error": "Code invalide"}

    return {"message": "Connexion réussie"}