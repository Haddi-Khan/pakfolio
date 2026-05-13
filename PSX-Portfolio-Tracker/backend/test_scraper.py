from database import create_tables
from data_providers.psx_scraper import scrape_all_history

print("Creating tables...")
create_tables()

print("Scraping history for 1 symbol to test...")
# Test with subset_limit=1 to just do the first symbol and verify insertion
scrape_all_history(subset_limit=1)
print("Done!")
