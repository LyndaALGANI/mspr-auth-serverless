import pyotp

def generate_2fa(username):
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="MSPR"
    )
    return secret, uri

def verify_2fa(secret, code):
    totp = pyotp.TOTP(secret)
    return totp.verify(code)