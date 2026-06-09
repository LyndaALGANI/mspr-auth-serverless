import json
import os
import io
import base64
from datetime import datetime
import psycopg2
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
    totp_code = body.get("totp_code")

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
        
        # Find user
        cur.execute("SELECT id, password, mfa, gendate, expired FROM users WHERE username = %s", (username,))
        user_row = cur.fetchone()
        
        if not user_row:
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "invalid_credentials"})
            }
        
        user_id, stored_encrypted_pw, mfa_secret, gendate, expired = user_row
        
        # Verify password
        try:
            cipher = get_cipher()
            decrypted_pw = cipher.decrypt(stored_encrypted_pw.encode()).decode()
        except Exception:
            decrypted_pw = None
            
        if decrypted_pw != password:
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "invalid_credentials"})
            }
            
        # Check password age/expiration
        is_expired = (expired == 1)
        if gendate:
            try:
                # Handle potential datetime or date formats
                if isinstance(gendate, str):
                    gen_dt = datetime.strptime(gendate, "%Y-%m-%d")
                else:
                    gen_dt = datetime.combine(gendate, datetime.min.time())
                days_old = (datetime.now() - gen_dt).days
                if days_old > 180:
                    is_expired = True
            except Exception:
                pass
                
        if is_expired:
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "expired_password", "expired": True})
            }
            
        # Verify 2FA
        if not mfa_secret:
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "mfa_not_configured"})
            }
            
        if not totp_code:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "totp_code is required"})
            }
            
        totp = pyotp.TOTP(mfa_secret)
        if not totp.verify(totp_code):
            return {
                "statusCode": 401,
                "headers": cors_headers,
                "body": json.dumps({"error": "invalid_totp"})
            }
            
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "status": "success",
                "message": "Authentification reussie"
            })
        }
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
