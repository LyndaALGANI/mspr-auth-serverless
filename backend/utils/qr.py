# import qrcode

# def generate_qr(data, filename):
#     img = qrcode.make(data)
#     img.save(filename)


import qrcode
import os

def generate_qr(data, filename):
    folder = "qrcodes"

    # créer dossier si n'existe pas
    if not os.path.exists(folder):
        os.makedirs(folder)

    path = os.path.join(folder, filename)

    img = qrcode.make(data)
    img.save(path)

    return path