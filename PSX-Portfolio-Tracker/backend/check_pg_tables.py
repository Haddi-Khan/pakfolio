import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    print("No DATABASE_URL found")
else:
    try:
        engine = create_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print("Tables:", tables)
    except Exception as e:
        print(f"Error: {e}")
