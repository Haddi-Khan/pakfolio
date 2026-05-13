import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../backend/.env'))

def upgrade_users_table():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set in environment or backend/.env")
        return

    # Replace postgres:// with postgresql:// if needed for SQLAlchemy
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    print(f"Connecting to database to run migrations...")
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        print("Adding is_verified column...")
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;"))
        
        print("Adding verification_token column...")
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR;"))
        
        print("Adding reset_token column...")
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR;"))
        
        print("Adding reset_token_expiry column...")
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP WITH TIME ZONE;"))
        
        print("Setting existing admin users to is_verified = TRUE...")
        conn.execute(text("UPDATE users SET is_verified = TRUE WHERE id = 1;"))
        
        print("Migration complete!")

if __name__ == "__main__":
    upgrade_users_table()
