import os
import sys

# Add backend to path so we can import models and database
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal
from models import User

def verify_user(username):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username.lower()).first()
        if user:
            user.is_verified = True
            user.verification_token = None
            db.commit()
            print(f"User {username} successfully verified.")
        else:
            print(f"User {username} not found.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_user("nasir41")
