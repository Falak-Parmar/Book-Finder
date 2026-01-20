import pandas as pd
import aiohttp
import asyncio
import json
import os
from pathlib import Path
import time

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_CSV_PATH = DATA_DIR / "raw" / "Accession Register-Books.csv"
OUTPUT_JSON_PATH = DATA_DIR / "processed" / "books_raw_enriched.json"
OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
CONCURRENCY_LIMIT = 20  # Increased for speed

async def search_openlibrary_async(session, query_params):
    """
    Async helper to perform the request.
    """
    try:
        headers = {'User-Agent': 'BookFinderApp/1.0 (falak@example.com)'}
        async with session.get(OPENLIBRARY_SEARCH_URL, params=query_params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('numFound', 0) > 0:
                    return data['docs'][0]
    except Exception as e:
        # print(f"Error requesting {query_params}: {e}") # Silent error for cleaner logs
        pass
    return None

async def fetch_book_details_smart_async(session, title, author):
    """
    Async version of the smart fetch strategy.
    """
    # 1. Strict Search
    res = await search_openlibrary_async(session, {'title': title, 'author': author, 'limit': 1})
    if res: return res, "Strict match"

    # 2. Relaxed/Short Title
    if ':' in title:
        short_title = title.split(':')[0].strip()
        res = await search_openlibrary_async(session, {'title': short_title, 'author': author, 'limit': 1})
        if res: return res, "Short Title + Author match"
    
    # 3. Title Only
    res = await search_openlibrary_async(session, {'title': title, 'limit': 1})
    if res: return res, "Title-only match"
    
    return None, "Not found"

# Global list to hold results
enriched_books = []
processed_ids = set()
processed_count = 0

def load_existing_progress():
    if OUTPUT_JSON_PATH.exists():
        try:
            with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("CRITICAL WARNING: JSON file exists but is corrupted (likely interrupted save).")
            print("Please fix or backup 'books_raw_enriched.json' manually before proceeding to avoid data loss.")
            print("Exiting to protect data.")
            exit(1)
    return []

def save_progress():
    """Save current progress atomically."""
    temp_path = OUTPUT_JSON_PATH.with_suffix('.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_books, f, indent=4)
    # Atomic rename
    os.replace(temp_path, OUTPUT_JSON_PATH)

async def process_row(session, semaphore, row, index, total):
    global processed_count
    
    local_id = str(row.get('Acc. No.', index))
    
    # Check if processed (redundant check for safety in concurrent env)
    if local_id in processed_ids:
        return

    title = row.get('Title', '')
    author = row.get('Author/Editor', '')
    
    if pd.isna(title) or not str(title).strip():
        return

    async with semaphore:
        # print(f"[{index+1}/{total}] Searching: '{title}'...") # Reduce noise for bulk
        result, method = await fetch_book_details_smart_async(session, title, author)
        
        # Simple logging
        status = "FOUND" if result else "MISSING"
        # Only print every 10th or if found to reduce noise, or just keep as is
        print(f"[{index+1}/{total}] {status} : {title[:40]}...")

        book_data = {
            'local_id': local_id,
            'original_title': title,
            'original_author': author,
            'api_data': result,
            'match_method': method,
            'found': bool(result)
        }
        
        enriched_books.append(book_data)
        processed_ids.add(local_id)
        processed_count += 1
        
        # Periodic Save
        if processed_count % 100 == 0:
            print(f"--- Saving progress ({len(enriched_books)} records) ---")
            save_progress()
            
        # Polite delay to keep average rate reasonable per connection
        await asyncio.sleep(0.2) 

async def ingest_books_async(sample_size=None):
    global enriched_books, processed_ids
    
    print(f"Reading CSV from {RAW_CSV_PATH}...")
    try:
        df = pd.read_csv(RAW_CSV_PATH)
    except FileNotFoundError:
        print("CSV not found.")
        return

    if sample_size:
        df = df.head(sample_size)
        
    enriched_books = load_existing_progress()
    processed_ids = {str(item['local_id']) for item in enriched_books}
    print(f"Resuming... {len(enriched_books)} records already processed.")
    
    # Create tasks
    tasks = []
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    print(f"Starting Async Ingestion with Concurrency={CONCURRENCY_LIMIT}...")
    async with aiohttp.ClientSession() as session:
        for index, row in df.iterrows():
            local_id = str(row.get('Acc. No.', index))
            if local_id in processed_ids:
                continue
            
            task = process_row(session, semaphore, row, index, len(df))
            tasks.append(task)
        
        # Run all
        if tasks:
            await asyncio.gather(*tasks)
        else:
            print("No new records to process.")
        
    save_progress()
    print(f"\nIngestion complete. Total records: {len(enriched_books)}")

def main():
    # Helper wrapper for sync entry point
    # Detect if loop is running (e.g. jupyter) - usually safe to just run
    asyncio.run(ingest_books_async(sample_size=None))

if __name__ == "__main__":
    main()
