import os
import sys
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal
from models import User
from schemas import ResendVerificationRequest

# Mocking the endpoint logic locally to avoid hitting Resend API
def test_resend_logic():
    print("Testing Resend Rate Limiting Logic...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "nasir41").first()
        if not user:
            print("User nasir41 not found. Please sign up first.")
            return

        # Reset for testing
        user.last_verification_sent_at = None
        user.verification_sent_count = 0
        db.commit()

        def try_resend(identifier):
            now = datetime.now(timezone.utc)
            if user.last_verification_sent_at:
                last_sent = user.last_verification_sent_at
                if last_sent.tzinfo is None: last_sent = last_sent.replace(tzinfo=timezone.utc)
                
                # Cooldown check
                if now - last_sent < timedelta(minutes=2):
                    diff = timedelta(minutes=2) - (now - last_sent)
                    return f"WAIT_{int(diff.total_seconds())}"
                
                # Daily limit check
                if now.date() == last_sent.date():
                    if user.verification_sent_count >= 5:
                        return "LIMIT_REACHED"
                    user.verification_sent_count += 1
                else:
                    user.verification_sent_count = 1
            else:
                user.verification_sent_count = 1
            
            user.last_verification_sent_at = now
            db.commit()
            return "SUCCESS"

        # 1. First attempt
        print(f"Attempt 1: {try_resend('nasir41')}")
        
        # 2. Immediate second attempt (should fail cooldown)
        print(f"Attempt 2 (immediate): {try_resend('nasir41')}")
        
        # 3. Simulate 5 attempts (bypass cooldown for testing counts)
        user.last_verification_sent_at = datetime.now(timezone.utc) - timedelta(minutes=3)
        user.verification_sent_count = 4
        db.commit()
        print(f"Attempt 5 (force cooldown bypass): {try_resend('nasir41')}")
        
        # 4. Immediate 6th attempt (should fail limit)
        user.last_verification_sent_at = datetime.now(timezone.utc) - timedelta(minutes=3)
        db.commit()
        print(f"Attempt 6 (force cooldown bypass): {try_resend('nasir41')}")

    finally:
        db.close()

if __name__ == "__main__":
    test_resend_logic()
