import json
import os
import random
import string
import io
import base64
import re
from datetime import datetime
import psycopg2
import qrcode
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
    if not username:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "username is required"})
        }

    # Validate username format (8 to 20 characters, letters, digits, _, -, .)
    if not re.match(r"^[a-zA-Z0-9_.-]{8,20}$", username):
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "invalid_username_format"})
        }

    # Generate 24-char password
    chars = string.ascii_letters + string.digits
    password = "".join(random.choice(chars) for _ in range(24))

    # Encrypt password
    cipher = get_cipher()
    encrypted_pw = cipher.encrypt(password.encode()).decode()

    # DB operation
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_row = cur.fetchone()
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        if user_row:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "username_already_exists"})
            }
        
        cur.execute(
            "INSERT INTO users (username, password, mfa, gendate, expired) VALUES (%s, %s, %s, %s, %s)",
            (username, encrypted_pw, "", today, 0)
        )
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

    # Generate QR Code for password
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(password)
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
