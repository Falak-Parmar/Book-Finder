import argparse
import requests
import os
import pandas as pd
import bibtexparser
from bs4 import BeautifulSoup
import logging
from typing import Optional

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
# Constants (Defaults)
OPAC_LIST_URL = "https://opac.daiict.ac.in/cgi-bin/koha/opac-shelves.pl?op=list&public=1"
DOWNLOAD_URL_TEMPLATE = "https://opac.daiict.ac.in/cgi-bin/koha/opac-downloadshelf.pl?shelfnumber={}&format=bibtex"
DEFAULT_SHELF_ID = "393"
DEFAULT_DATA_DIR = "data/raw/new_arrivals"
DEFAULT_CSV_PATH = "data/raw/Accession Register-Books.csv"

def get_shelf_id() -> str:
    """
    Crawls the OPAC list page to find the 'New Arrivals' shelf ID.
    Returns the found ID or the default ID if not found or on error.
    """
    try:
        logger.info(f"Crawling {OPAC_LIST_URL} to find 'New Arrivals' shelf ID...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        response = requests.get(OPAC_LIST_URL, timeout=10, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the link containing "New Arrivals" (case insensitive)
        for a in soup.find_all('a', href=True):
            if "new arrivals" in a.get_text().lower():
                href = a['href']
                # href format: /cgi-bin/koha/opac-shelves.pl?op=view&shelfnumber=393
                if "shelfnumber=" in href:
                    shelf_id = href.split("shelfnumber=")[1].split("&")[0]
                    logger.info(f"Found 'New Arrivals' shelf ID: {shelf_id}")
                    return shelf_id
        
        logger.warning("Could not find 'New Arrivals' link in the page. Using default ID.")
        return DEFAULT_SHELF_ID

    except Exception as e:
        logger.error(f"Error crawling for shelf ID: {e}. Using default ID.")
        return DEFAULT_SHELF_ID

def download_bibtex(shelf_id: str, data_dir: str) -> Optional[str]:
    """
    Downloads the BibTeX file for the given shelf ID.
    Checks if the response is actually a BibTeX file and not a security check page.
    """
    url = DOWNLOAD_URL_TEMPLATE.format(shelf_id)
    logger.info(f"Downloading BibTeX from {url}...")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/plain,application/x-bibtex,*/*"
        }
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        
        content = response.content.decode('utf-8', errors='ignore')
        
        # Check if it looks like a BibTeX file (starts with @)
        # If it looks like HTML (starts with <!DOCTYPE or <html), it's likely a security check
        if content.strip().startswith("<") or "Security Check" in content:
            logger.warning("Security Check detected (Altcha). Download ignored to protect existing data.")
            logger.warning("Please visit the OPAC in your browser to clear the check if this persists.")
            return None

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        output_file = os.path.join(data_dir, "new_arrivals.bib")
        with open(output_file, "wb") as f:
            f.write(response.content)
            
        logger.info(f"Downloaded BibTeX to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error downloading BibTeX: {e}")
        return None

def parse_and_append(bib_file: str, csv_path: str) -> int:
    """
    Parses the BibTeX file and appends new entries to the CSV.
    Returns the number of new records added.
    """
    if not os.path.exists(bib_file):
        logger.error(f"BibTeX file {bib_file} not found.")
        return 0

    logger.info("Parsing BibTeX file...")
    with open(bib_file, 'r', encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    if not bib_database.entries:
        logger.warning("No entries found in BibTeX file.")
        return 0

    # Load existing CSV to check for duplicates
    if os.path.exists(csv_path):
        try:
            df_existing = pd.read_csv(csv_path)
            # Ensure Acc. No. is string for comparison
            existing_acc_nos = set(df_existing['Acc. No.'].astype(str).tolist())
        except Exception as e:
            logger.error(f"Error reading existing CSV: {e}")
            return 0
    else:
        existing_acc_nos = set()
        df_existing = pd.DataFrame(columns=["Acc. No.", "Author/Editor", "Title"])

    new_rows = []
    
    for entry in bib_database.entries:
        bib_id = entry.get('ID', '')
        acc_no = bib_id.strip()
        
        if acc_no in existing_acc_nos:
            logger.debug(f"Skipping existing Acc. No.: {acc_no}")
            continue

        title = entry.get('title', '').strip()
        author = entry.get('author', '').strip()
        
        new_row = {
            "Acc. No.": acc_no,
            "Author/Editor": author,
            "Title": title
        }
        new_rows.append(new_row)
        existing_acc_nos.add(acc_no)

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        # Create full DF with all columns from existing
        df_final = pd.DataFrame(new_rows, columns=df_existing.columns)
        
        # Append to main CSV
        output_mode = 'a'
        header = not os.path.exists(csv_path)
        df_final.to_csv(csv_path, mode=output_mode, header=header, index=False)
        logger.info(f"Appended {len(new_rows)} new records to {csv_path}.")

        # Save to temporary "sync" file for incremental enrichment
        sync_csv = os.path.join(os.path.dirname(csv_path), "current_sync.csv")
        df_final.to_csv(sync_csv, index=False)
        logger.info(f"Saved {len(new_rows)} records to {sync_csv} for incremental processing.")
        
        return len(new_rows)
    else:
        logger.info("No new records found to append.")
        return 0

def run_sync(shelf_id=None, data_dir=DEFAULT_DATA_DIR, csv_path=DEFAULT_CSV_PATH):
    """Main function to run the sync pipeline."""
    if not shelf_id:
        shelf_id = get_shelf_id()
    
    bib_file = download_bibtex(shelf_id, data_dir)
    
    # Even if download fails, check if the file exists (maybe manually added)
    expected_bib_file = os.path.join(data_dir, "new_arrivals.bib")
    if not bib_file and os.path.exists(expected_bib_file):
        logger.info(f"Using existing BibTeX file: {expected_bib_file}")
        bib_file = expected_bib_file

    if bib_file:
        new_count = parse_and_append(bib_file, csv_path)
        if new_count > 0:
            # Exit with code 2 to indicate "Items Added" to the orchestrator
            return 2
    else:
        logger.error("Sync failed due to download error.")
        return 1
    
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Data from OPAC")
    parser.add_argument("--shelf-id", help="Manually specify shelf ID")
    parser.add_argument("--output-dir", default=DEFAULT_DATA_DIR, help="Directory to save downloaded BibTeX")
    parser.add_argument("--csv-path", default=DEFAULT_CSV_PATH, help="Path to main csv register")
    
    args = parser.parse_args()
    
    exit_code = run_sync(args.shelf_id, args.output_dir, args.csv_path)
    import sys
    sys.exit(exit_code)
