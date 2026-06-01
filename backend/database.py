import sqlite3
import os

# Base de données locale dans le dossier backend
DB_PATH = os.path.join(os.path.dirname(__file__), "mspr.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Créer la table si elle n'existe pas encore
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT    NOT NULL UNIQUE,
        password TEXT    NOT NULL,
        MFA      TEXT    NOT NULL DEFAULT '',
        gendate  TEXT    NOT NULL,
        expired  INTEGER NOT NULL DEFAULT 0
    )
""")
conn.commit()

print("Connexion SQLite OK")
