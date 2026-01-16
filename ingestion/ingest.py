import pandas as pd
import requests
import time
import json
import os
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_CSV_PATH = DATA_DIR / "raw" / "Accession Register-Books.csv"
OUTPUT_JSON_PATH = DATA_DIR / "processed" / "books_raw_enriched.json"
OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"

def search_openlibrary(query_params):
    """
    Helper to perform the request.
    """
    try:
        headers = {'User-Agent': 'BookFinderApp/1.0 (falak@example.com)'}
        response = requests.get(OPENLIBRARY_SEARCH_URL, params=query_params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('numFound', 0) > 0:
                return data['docs'][0]
    except Exception as e:
        print(f"Error requesting {query_params}: {e}")
    return None

def fetch_book_details_smart(title, author):
    """
    Try multiple strategies to find the book.
    """
    # 1. Strict Search: Title AND Author
    res = search_openlibrary({'title': title, 'author': author, 'limit': 1})
    if res: return res, "Strict match"

    # 2. Relaxed Author (just surname if possible, or skip author if very strict)
    # Let's try Title Only first if it's unique enough, but might be too broad.
    # Let's try Cleaning the title (remove part after :)
    if ':' in title:
        short_title = title.split(':')[0].strip()
        res = search_openlibrary({'title': short_title, 'author': author, 'limit': 1})
        if res: return res, "Short Title + Author match"
    
    # 3. Title Only Search (General query 'q') - risky but better than nothing
    # res = search_openlibrary({'q': title, 'limit': 1})
    # if res: return res.get('docs', [None])[0], "Title 'q' match"

    # 4. Fallback: Search by just Title (field)
    res = search_openlibrary({'title': title, 'limit': 1})
    if res: return res, "Title-only match"
    
    return None, "Not found"

def ingest_books(sample_size=10):
    print(f"Reading CSV from {RAW_CSV_PATH}...")
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        df = pd.read_csv(RAW_CSV_PATH)
    except FileNotFoundError:
        print(f"Error: File not found at {RAW_CSV_PATH}")
        return

    if sample_size:
        df = df.head(sample_size)
        print(f"Processing first {sample_size} rows for testing...")

    enriched_books = []
    
    for index, row in df.iterrows():
        title = row.get('Title', '')
        author = row.get('Author/Editor', '')
        
        if pd.isna(title) or not str(title).strip():
            continue
            
        print(f"[{index+1}/{len(df)}] Searching: '{title}'...")
        
        result, method = fetch_book_details_smart(title, author)
        
        book_data = {
            'local_id': row.get('Acc. No.', index),
            'original_title': title,
            'original_author': author,
            'api_data': result,
            'match_method': method,
            'found': bool(result)
        }
        
        if result:
            print(f"   -> Found ({method}): {result.get('title', 'N/A')}")
        else:
            print("   -> Not found.")
            
        enriched_books.append(book_data)
        time.sleep(1.0) # Rate limit
        
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(enriched_books, f, indent=4)
        
    print(f"\nIngestion complete. Saved {len(enriched_books)} records.")

if __name__ == "__main__":
    ingest_books(sample_size=5)
