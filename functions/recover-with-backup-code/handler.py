import json
import os
import random
import string
import io
import base64
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
    backup_code = body.get("backup_code")

    if not username or not backup_code:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "username and backup_code are required"})
        }

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Find user
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_row = cur.fetchone()
        
        if not user_row:
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "invalid_credentials"})
            }
            
        user_id = user_row[0]
        
        # Get unused backup codes for this user
        cur.execute("SELECT id, code FROM backup_codes WHERE user_id = %s AND used = FALSE", (user_id,))
        codes_rows = cur.fetchall()
        
        matched_id = None
        cipher = get_cipher()
        
        for code_id, enc_code in codes_rows:
            try:
                decrypted_code = cipher.decrypt(enc_code.encode()).decode()
                if decrypted_code.upper() == backup_code.upper().strip():
                    matched_id = code_id
                    break
            except Exception:
                pass
                
        if not matched_id:
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "invalid_backup_code"})
            }
            
        # Update matching backup code to used
        cur.execute("UPDATE backup_codes SET used = TRUE WHERE id = %s", (matched_id,))
        
        # Generate new random 12-char password
        chars = string.ascii_letters + string.digits
        new_password = "".join(random.choice(chars) for _ in range(12))
        
        # Encrypt and save new password
        encrypted_pw = cipher.encrypt(new_password.encode()).decode()
        today = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute(
            "UPDATE users SET password = %s, expired = 0, gendate = %s WHERE id = %s",
            (encrypted_pw, today, user_id)
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

    # Generate QR Code for the new password
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(new_password)
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
