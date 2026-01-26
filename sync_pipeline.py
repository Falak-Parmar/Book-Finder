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
OPAC_LIST_URL = "https://opac.daiict.ac.in/cgi-bin/koha/opac-shelves.pl?op=list&public=1"
DOWNLOAD_URL_TEMPLATE = "https://opac.daiict.ac.in/cgi-bin/koha/opac-downloadshelf.pl?shelfnumber={}&format=bibtex"
DEFAULT_SHELF_ID = "393"
DATA_DIR = "data/raw/new_arrivals"
CSV_PATH = "data/raw/Accession Register-Books.csv"
NEW_ARRIVALS_FILE = os.path.join(DATA_DIR, "new_arrivals.bib")

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

def download_bibtex(shelf_id: str) -> Optional[str]:
    """
    Downloads the BibTeX file for the given shelf ID.
    """
    url = DOWNLOAD_URL_TEMPLATE.format(shelf_id)
    logger.info(f"Downloading BibTeX from {url}...")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        with open(NEW_ARRIVALS_FILE, "wb") as f:
            f.write(response.content)
            
        logger.info(f"Downloaded BibTeX to {NEW_ARRIVALS_FILE}")
        return NEW_ARRIVALS_FILE
        
    except Exception as e:
        logger.error(f"Error downloading BibTeX: {e}")
        return None

def parse_and_append(bib_file: str):
    """
    Parses the BibTeX file and appends new entries to the CSV.
    """
    if not os.path.exists(bib_file):
        logger.error(f"BibTeX file {bib_file} not found.")
        return

    logger.info("Parsing BibTeX file...")
    with open(bib_file, 'r', encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    if not bib_database.entries:
        logger.warning("No entries found in BibTeX file.")
        return

    # Load existing CSV to check for duplicates
    if os.path.exists(CSV_PATH):
        try:
            df_existing = pd.read_csv(CSV_PATH)
            # Ensure Acc. No. is string for comparison
            existing_acc_nos = set(df_existing['Acc. No.'].astype(str).tolist())
        except Exception as e:
            logger.error(f"Error reading existing CSV: {e}")
            return
    else:
        existing_acc_nos = set()
        df_existing = pd.DataFrame(columns=["Acc. No.", "Author/Editor", "Title"])

    new_rows = []
    
    for entry in bib_database.entries:
        # Extract Acc. No. from ID (e.g., "34341" from "34341" or "book:34341")
        # The ID in bibtexparser is in entry['ID']
        bib_id = entry.get('ID', '')
        
        # Assumption: The ID is the Acc. No. or contains it.
        # Based on user feedback: "the first value (rn a 5 digit number) is the acc. no."
        acc_no = bib_id.strip()
        
        if acc_no in existing_acc_nos:
            logger.debug(f"Skipping existing Acc. No.: {acc_no}")
            continue

        title = entry.get('title', '').strip()
        author = entry.get('author', '').strip()
        
        # Normalize author: BibTeX often has "Last, First", CSV might want "First Last" or keep as is.
        # User's CSV seems to have "Author/Editor". I'll keep it as is from BibTeX for now.
        
        new_row = {
            "Acc. No.": acc_no,
            "Author/Editor": author,
            "Title": title
            # Add other columns if needed matching CSV structure, but these are the minimal required for ingestion
        }
        new_rows.append(new_row)
        existing_acc_nos.add(acc_no) # Prevent internal duplicates in the same batch

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        # Ensure only columns that exist in the target CSV are saved (or align them)
        # Actually, simpler to just append columns that match.
        
        # We should align with existing CSV columns to avoid issues
        # Create a DataFrame with all columns from existing, filled with NaN
        df_final = pd.DataFrame(new_rows, columns=df_existing.columns)
        
        # Append to CSV
        output_mode = 'a'
        header = not os.path.exists(CSV_PATH)
        
        df_final.to_csv(CSV_PATH, mode=output_mode, header=header, index=False)
        logger.info(f"Appended {len(new_rows)} new records to {CSV_PATH}.")
    else:
        logger.info("No new records found to append.")

def run_sync():
    """Main function to run the sync pipeline."""
    shelf_id = get_shelf_id()
    bib_file = download_bibtex(shelf_id)
    if bib_file:
        parse_and_append(bib_file)
    else:
        logger.error("Sync failed due to download error.")

if __name__ == "__main__":
    run_sync()
