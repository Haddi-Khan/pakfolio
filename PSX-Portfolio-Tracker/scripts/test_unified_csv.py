import os
import sys
import csv
import io
from datetime import date

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

import crud
from database import SessionLocal
from models import TradeAction, TradeType, AssetType, CashTxType
from schemas import TradeCreate, CashTxCreate

def test_unified_csv():
    print("Testing Unified CSV Import/Export...")
    db = SessionLocal()
    try:
        # 1. Create a dummy portfolio
        from models import User, Portfolio
        user = db.query(User).first()
        if not user:
            print("No user found, cannot test.")
            return
            
        p = Portfolio(user_id=user.id, name="Test CSV Portfolio")
        db.add(p)
        db.commit()
        db.refresh(p)
        pid = p.id
        print(f"Created Test Portfolio ID: {pid}")

        # 2. Add a Trade and a Cash Tx
        t_data = TradeCreate(
            symbol="TRG", action=TradeAction.BUY, price=100.0, quantity=10.0, 
            trade_date=date.today(), asset_type=AssetType.STOCK
        )
        crud.create_trade(db, pid, t_data)
        
        c_data = CashTxCreate(
            tx_type=CashTxType.DEPOSIT, amount=50000.0, tx_date=date.today(), description="Initial"
        )
        crud.create_cash_tx(db, pid, c_data)
        print("Added 1 trade and 1 deposit.")

        # 3. Simulate Import of a Unified CSV
        csv_content = """date,type,symbol,action,price_amount,quantity,deductions,notes
2026-03-01,TRADE,ENGRO,BUY,300.0,5,0,Backup Trade
2026-03-02,CASH,CASH,DEPOSIT,25000.0,1.0,0,Salary Deposit
"""
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        for row in reader:
            row_type = row["type"].upper()
            if row_type == "TRADE":
                trade_data = TradeCreate(
                    symbol=row["symbol"], action=row["action"], 
                    price=float(row["price_amount"]), quantity=float(row["quantity"]),
                    trade_date=date.fromisoformat(row["date"]), notes=row["notes"]
                )
                crud.create_trade(db, pid, trade_data)
            elif row_type == "CASH":
                cash_data = CashTxCreate(
                    tx_type=row["action"], amount=float(row["price_amount"]),
                    tx_date=date.fromisoformat(row["date"]), description=row["notes"]
                )
                crud.create_cash_tx(db, pid, cash_data)
        
        print("Imported 2 rows from unified CSV template.")

        # 4. Verify trades and cash count
        trades = crud.get_trades(db, pid)
        cash = crud.get_cash_transactions(db, pid)
        
        print(f"Final Count - Trades: {len(trades)}, Cash: {len(cash)}")
        
        if len(trades) == 2 and len(cash) == 2:
            print("SUCCESS: Both trades and cash transactions were processed correctly.")
        else:
            print(f"FAILURE: Expected 2/2, got {len(trades)}/{len(cash)}")

        # Cleanup
        db.delete(p)
        db.commit()
        print("Cleaned up test portfolio.")

    finally:
        db.close()

if __name__ == "__main__":
    test_unified_csv()
