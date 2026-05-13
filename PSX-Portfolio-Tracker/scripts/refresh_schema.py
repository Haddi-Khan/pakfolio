import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from database import engine
from models import Base

print("Dropping all tables...")
Base.metadata.drop_all(engine)
print("Creating all tables with new schema...")
Base.metadata.create_all(engine)
print("Done!")
