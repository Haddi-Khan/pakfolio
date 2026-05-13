import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal
from models import User, Portfolio

def delete_user_by_username(username):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username.lower()).first()
        if not user:
            print(f"User '{username}' not found.")
            return

        print(f"Deleting user '{username}' (ID: {user.id}) and all associated data...")
        # SQLAlchemy cascade handles portfolios, trades, etc.
        db.delete(user)
        db.commit()
        print("Successfully deleted user.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    delete_user_by_username("nasir41")
