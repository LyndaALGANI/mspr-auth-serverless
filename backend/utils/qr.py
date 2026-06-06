import qrcode
import os

DATA_DIR = os.getenv("DATA_DIR", "/tmp/mspr-data")
QR_DIR = os.path.join(DATA_DIR, "qrcodes")
os.makedirs(QR_DIR, exist_ok=True)

def generate_qr(data, filename):
    path = os.path.join(QR_DIR, filename)

    img = qrcode.make(data)
    img.save(path)

    return path