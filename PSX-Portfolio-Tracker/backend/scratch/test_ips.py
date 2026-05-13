import os
from sqlalchemy import create_engine, text

URL1 = "postgresql://postgres.qppdpbmhjzlrbncurckw:z4v6V_pN!tLDz8A@13.239.87.90:6543/postgres?sslmode=require"
URL2 = "postgresql://postgres.qppdpbmhjzlrbncurckw:z4v6V_pN!tLDz8A@52.65.247.42:6543/postgres?sslmode=require"

print("Testing IP1 (13.239.87.90)...")
try:
    engine = create_engine(URL1, connect_args={"connect_timeout": 5})
    with engine.connect() as conn:
        print("IP1 Success: ", conn.execute(text("SELECT 1")).scalar())
except Exception as e:
    print("IP1 failed: ", e)

print("\nTesting IP2 (52.65.247.42)...")
try:
    engine = create_engine(URL2, connect_args={"connect_timeout": 5})
    with engine.connect() as conn:
        print("IP2 Success: ", conn.execute(text("SELECT 1")).scalar())
except Exception as e:
    print("IP2 failed: ", e)
