import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-58IOMQ0;"
    "DATABASE=mspr;"
    "Trusted_Connection=yes;"
)
print("Connexion SQL Server OK")
cursor = conn.cursor()

