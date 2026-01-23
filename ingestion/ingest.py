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
# OpenAlex Config
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CONCURRENCY_LIMIT = 50
EMAIL_CONTACT = "falak.parmar.bookfinder.proj@gmail.com" 

def reconstruct_abstract(inverted_index):
    """
    Reconstruct abstract text from OpenAlex's inverted index.
    """
    if not inverted_index:
        return None
    word_index = []
    for k, v in inverted_index.items():
        for index in v:
            word_index.append([k, index])
    word_index = sorted(word_index, key=lambda x: x[1])
    return " ".join(map(lambda x: x[0], word_index))

async def search_openalex_async(session, title, author):
    """
    Search OpenAlex for a work matching title and author.
    """
    if not title: return None
    
    # Cleaning Strategy
    clean_title = title.replace('...', '').strip()
    if ':' in clean_title:
        clean_title = clean_title.split(':')[0].strip()
        
    strategies = []
    
    # 1. Title + Author (Strict)
    clean_author = ""
    if author and pd.notna(author):
        clean_author = str(author).split(',')[0].strip() # Surname
        
    if clean_author:
        strategies.append([f"title.search:{clean_title}", f"authorships.author.display_name.search:{clean_author}"])
        
    # 2. Title Only (Relaxed)
    strategies.append([f"title.search:{clean_title}"])
    
    # 3. Aggressive Truncation
    words = clean_title.split()
    if len(words) > 5:
        short_title = " ".join(words[:5])
        if clean_author:
            strategies.append([f"title.search:{short_title}", f"authorships.author.display_name.search:{clean_author}"])
        strategies.append([f"title.search:{short_title}"])
        
    # API KEY handling
    api_key = os.environ.get("OPENALEX_API_KEY")
    headers = {}
    if api_key:
        headers['api_key'] = api_key

    for filters in strategies:
        filter_str = ",".join(filters)
        params = {
            'filter': filter_str,
            'per_page': 1,
            'mailto': EMAIL_CONTACT
        }
        try:
            async with session.get(OPENALEX_WORKS_URL, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    if results:
                        return results[0]
                elif response.status == 429:
                    # Rate limit hit
                    await asyncio.sleep(1)
        except Exception:
            pass
            
    return None

# Global list to hold results
enriched_books = []
processed_ids = set()
processed_count = 0

def load_existing_progress():
    if OUTPUT_JSON_PATH.exists():
        try:
            # Check file size. If > 100MB, maybe warn? 
            # But we are fixing the bloat now.
            with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError:
            return []
    return []

def save_progress():
    """Save current progress atomically."""
    temp_path = OUTPUT_JSON_PATH.with_suffix('.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_books, f, indent=4)
    os.replace(temp_path, OUTPUT_JSON_PATH)

async def process_row(session, semaphore, row, index, total):
    global processed_count
    
    local_id = str(row.get('Acc. No.', index))
    
    if local_id in processed_ids:
        return

    title = row.get('Title', '')
    author = row.get('Author/Editor', '')
    
    if pd.isna(title) or not str(title).strip():
        return

    async with semaphore:
        # Search OpenAlex
        result = await search_openalex_async(session, title, author)
        
        found = bool(result)
        abstract = None
        if result:
            # Reconstruct abstract but KEEP full result
            abstract = reconstruct_abstract(result.get('abstract_inverted_index'))
            
        status = "FOUND" if found else "MISSING"
        if abstract: status += "+ABS"
        
        # Log less frequently or clearly
        if processed_count % 50 == 0:
            print(f"[{index+1}/{total}] {status} : {title[:40]}...")

        book_data = {
            'local_id': local_id,
            'original_title': title,
            'original_author': author,
            'api_data': result, # Full OpenAlex object (Unpruned)
            'openalex_abstract': abstract, # Helper field
            'found': found,
            'source': 'openalex'
        }
        
        enriched_books.append(book_data)
        processed_ids.add(local_id)
        processed_count += 1
        
        if processed_count % 200 == 0:
            print(f"--- Saving progress ({len(enriched_books)} records) ---")
            save_progress()
            
        await asyncio.sleep(0.1) # OpenAlex is fast

async def ingest_books_async(sample_size=5):
    global enriched_books, processed_ids
    
    print(f"Reading CSV from {RAW_CSV_PATH}...")
    try:
        df = pd.read_csv(RAW_CSV_PATH)
    except FileNotFoundError:
        print("CSV not found.")
        return

    # START FRESH if sampling (optional preference, but good for testing new API)
    # The user said "Sample it for 5 books", implying a test run.
    # We will reset global lists if sample_size is small to show clear results.
    # For now, if we changed schema (Pruning), it is best to start fresh 
    # OR strictly only prune new ones. 
    # But since user complained about size, let's force fresh start if sample_size is small.
    if sample_size and sample_size <= 20:
        print("Sampling mode: Starting fresh.")
        enriched_books = []
        processed_ids = set()
    else:
        enriched_books = load_existing_progress()
        # Note: loading existing big files might be an issue if mixed, 
        # but `clean.py` should handle extra fields gracefully (ignore them).
        processed_ids = {str(item['local_id']) for item in enriched_books}
        print(f"Resuming... {len(enriched_books)} records already processed.")

    if sample_size:
        df = df.head(sample_size)
    
    tasks = []
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    print(f"Starting OpenAlex Ingestion (Sample={sample_size})...")
    async with aiohttp.ClientSession() as session:
        for index, row in df.iterrows():
            local_id = str(row.get('Acc. No.', index))
            if local_id in processed_ids:
                continue
            
            task = process_row(session, semaphore, row, index, len(df))
            tasks.append(task)
        
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
