import sqlite3
import os

db_path = 'psx_portfolio.db'
if not os.path.exists(db_path):
    print(f"File {db_path} does not exist.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", [t[0] for t in tables])
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
