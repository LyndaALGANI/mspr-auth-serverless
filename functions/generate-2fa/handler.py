import json
import os
import io
import base64
import psycopg2
import qrcode
import pyotp
from cryptography.fernet import Fernet

def get_cipher():
    secret_path = "/var/openfaas/secrets/encryption-key"
    if os.path.exists(secret_path):
        with open(secret_path, "rb") as f:
            key = f.read().strip()
    else:
        key = os.getenv("ENCRYPTION_KEY", "Rt9LIv0sl8hVk_UjrxDB2QoACvrPoJmVVxuM5OdM5_o=").encode()
    return Fernet(key)

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(db_url)

def handle(event, context):
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    if event.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": ""
        }

    if event.method != "POST":
        return {
            "statusCode": 405,
            "headers": cors_headers,
            "body": json.dumps({"error": "Method Not Allowed"})
        }

    try:
        body = json.loads(event.body.decode('utf-8')) if isinstance(event.body, bytes) else json.loads(event.body)
    except Exception:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "Invalid JSON body"})
        }

    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "username and password are required"})
        }

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user details (including stored password)
        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user_row = cur.fetchone()
        
        if not user_row:
            return {
                "statusCode": 404,
                "headers": cors_headers,
                "body": json.dumps({"error": "User not found"})
            }
        
        user_id, stored_encrypted_pw = user_row

        # Verify password
        try:
            cipher = get_cipher()
            decrypted_pw = cipher.decrypt(stored_encrypted_pw.encode()).decode()
        except Exception:
            decrypted_pw = None
            
        if decrypted_pw != password:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "invalid_password"})
            }

        # Generate TOTP Secret
        totp_secret = pyotp.random_base32()
        totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=username, issuer_name="COFRAP")

        # Update user's TOTP secret in DB
        cur.execute("UPDATE users SET mfa = %s WHERE id = %s", (totp_secret, user_id))
        
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Database error: {str(e)}"})
        }
    finally:
        if conn:
            conn.close()

    # Generate QR Code image for TOTP URI
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {
        "statusCode": 200,
        "headers": cors_headers,
        "body": json.dumps({
            "qr_code": qr_base64
        })
    }
