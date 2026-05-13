import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal
from models import User, Portfolio, CashTransaction, CashTxType
from schemas import PortfolioCreate
import crud

def verify():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "nasir41").first()
        if not user:
            print("User nasir41 not found")
            return

        print(f"Testing portfolio creation with balance for user: {user.username}")
        
        # Test creation
        p = crud.create_portfolio(
            db, 
            PortfolioCreate(name="Initial Balance Test", initial_balance=50000.0), 
            user.id
        )
        print(f"Portfolio created: ID={p.id}, Name={p.name}")
        
        # Verify deposit
        tx = db.query(CashTransaction).filter(
            CashTransaction.portfolio_id == p.id,
            CashTransaction.tx_type == CashTxType.DEPOSIT
        ).first()
        
        if tx and tx.amount == 50000.0:
            print(f"SUCCESS: Deposit of {tx.amount} found for portfolio.")
        else:
            print("FAILURE: No deposit found or amount mismatch.")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify()
