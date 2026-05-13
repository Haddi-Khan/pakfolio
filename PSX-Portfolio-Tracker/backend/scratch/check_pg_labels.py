
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv('DATABASE_URL')
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname = 'assettype'")
    print(cur.fetchall())
except Exception as e:
    print(f"Error: {e}")
