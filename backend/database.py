import sqlite3
import os

DATA_DIR = os.getenv("DATA_DIR", "/tmp/mspr-data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "mspr.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

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

print(f"Connexion SQLite OK : {DB_PATH}")
