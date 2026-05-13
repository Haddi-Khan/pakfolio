import logging
from data_providers.psx_scraper import scrape_all_history

# Setup logging to see the output in your terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    print("Starting the bulk historical PSX scraper...")
    print("This will fetch data for all symbols and save it into the history_psx table.")
    print("Press Ctrl+C to cancel at any time.\n")
    
    # Run the full scraper for all symbols
    scrape_all_history()
    
    print("\nScraping complete!")
