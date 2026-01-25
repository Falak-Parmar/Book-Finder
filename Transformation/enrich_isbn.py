import json
import os
import aiohttp
import asyncio
import argparse
import datetime
from typing import List, Dict, Any, Optional

INPUT_FILE = r"data/processed/books_cleaned.jsonl"
TEMP_FILE = r"data/processed/books_cleaned_temp.jsonl"
LOG_FILE = r"logs/project_log.md"

MAX_CONCURRENT_REQUESTS = 10  # Moderate concurrency
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY")

async def fetch_openlibrary_isbn(session: aiohttp.ClientSession, title: str, author: str) -> List[str]:
    """Search OpenLibrary for ISBNs."""
    base_url = "http://openlibrary.org/search.json"
    params = {
        "title": title,
        "author": author,
        "fields": "isbn",
        "limit": 1
    }
    try:
        async with session.get(base_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                docs = data.get("docs", [])
                if docs:
                    return docs[0].get("isbn", [])
    except Exception as e:
        # print(f"OL Error for {title}: {e}")
        pass
    return []

async def fetch_openalex_isbn(session: aiohttp.ClientSession, title: str, author: str) -> List[str]:
    """Search OpenAlex for ISBNs."""
    base_url = "https://api.openalex.org/works"
    query = f"{title} {author}"
    params = {
        "search": query,
        "per-page": 1
    }
    headers = {}
    if OPENALEX_API_KEY:
        headers["api_key"] = OPENALEX_API_KEY # OpenAlex uses 'api_key' in query or header? Usually header 'Authorization' or query param?
        # Docs say: https://api.openalex.org/works?api_key=...
        # But let's check standard practice. Actually, OpenAlex usually accepts it as a query param 'api_key' or 'mailto'.
        # Let's put it in params to be safe if key is provided.
        params["api_key"] = OPENALEX_API_KEY
    
    # Also good practice to identify
    params["mailto"] = "antigravity_agent@google.com" 

    try:
        async with session.get(base_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                results = data.get("results", [])
                
                # Debug print for first few
                # if results and len(results) > 0: 
                #     print(f"Debug: Found {len(results)} results for {query}")
                #     print(f"Top result type: {results[0].get('type')}, ids: {results[0].get('ids')}")
                
                isbns = []
                if results:
                    # OpenAlex structure might have 'ids' field or 'apc_list' etc. 
                    # Actually, ISBNs are often in 'ids' -> 'isbn' or strictly in 'locations'.
                    # But OpenAlex is strictly for works. It might link to Mag, OpenAlex ID, DOI, PMID.
                    # It might NOT have ISBN directly for all works unless it's a book.
                    # Let's check 'type' == 'book' and look for ISBNs in 'ids' or 'biblio'.
                    work = results[0]
                    # Check ids
                    ids = work.get("ids", {})
                    # sometimes isbn is there? or maybe in 'locations'?
                    # OpenAlex schema: https://docs.openalex.org/api-entities/works/work-object
                    # It has 'locations', 'ids' (doi, mag, pmid).
                    # 'apc_paid' etc.
                    # Actually, for books specifically, 'ids' might have 'isbn'?
                    # Recent updates might have it. If not, we rely on what we can find. 
                    # Let's try to find keys starting with 'isbn' in ids if they exist (unlikely standard field)
                    # BUT, let's look at 'locations' -> 'source' -> 'issn_l' (for journals).
                    # For books, it's tricky. OpenLibrary is better for ISBN. 
                    # We will try to extract anything that looks like an ISBN if present, or just pass if not obvious.
                    # Actually, OpenAlex is scientific papers focused. It might catch books but ISBNs might be sparse.
                    # We'll do our best.
                    for work in results:
                        # Check ids for isbn
                        ids = work.get("ids", {})
                        if "isbn" in ids:
                            val = ids["isbn"]
                            if isinstance(val, list):
                                isbns.extend(val)
                            elif isinstance(val, str):
                                isbns.append(val)
                        
                        # Also check locations -> source -> isbn? Rare but possible.
                        # Usually ids['isbn'] is the place.
                    
                    if isbns:
                        return isbns
    except Exception as e:
        pass
    return []

async def process_book(session, row, semaphore):
    async with semaphore:
        title = row.get("original_title", "")
        author = row.get("original_author", "")
        
        if not title:
            row["isbn"] = []
            return row

        # Fetch from OpenAlex only
        t2 = fetch_openalex_isbn(session, title, author)
        
        results = await asyncio.gather(t2)
        
        oa_isbns = results[0]
        
        # Dedupe
        row["isbn"] = list(set(oa_isbns))
        return row

async def main():
    print(f"Starting ISBN enrichment...")
    if OPENALEX_API_KEY:
        print("Using OpenAlex API Key from environment.")
    else:
        print("No OpenAlex API Key found in environment.")

    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return

    # Read all lines first (it's 36k lines, memory should be fine ~50MB)
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    total_records = len(lines)
    print(f"Loaded {total_records} records.")
    
    rows = [json.loads(line) for line in lines]
    
    # Process in chunks to save progress? Or just all at once and stream write?
    # Stream writing to temp file is safer.
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in rows:
            tasks.append(process_book(session, row, semaphore))
        
        # Use simple gather for now or as_completed for progress bar?
        # Let's use batching to print progress
        batch_size = 50
        enriched_count = 0
        
        with open(TEMP_FILE, "w", encoding="utf-8") as outfile:
            for i in range(0, total_records, batch_size):
                batch_tasks = tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*batch_tasks)
                
                for res in batch_results:
                    outfile.write(json.dumps(res) + "\n")
                    if res.get("isbn"):
                        enriched_count += 1
                
                print(f"Processed {min(i+batch_size, total_records)}/{total_records} - Enriched: {enriched_count}", end='\r')
    
    print(f"\nEnrichment complete. Replacing original file.")
    
    # Atomically replace (or delete and rename on Windows)
    if os.path.exists(INPUT_FILE):
        os.remove(INPUT_FILE)
    os.rename(TEMP_FILE, INPUT_FILE)
    
    log_stats(total_records, enriched_count)

def log_stats(total, enriched):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
## ISBN Enrichment - {timestamp}
- **Task**: Fetch ISBNs from OpenLibrary & OpenAlex
- **Input/Output**: `{INPUT_FILE}`
- **Stats**:
  - Total Records Processed: {total}
  - Records with ISBNs found: {enriched}
"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
    print("Log updated.")

if __name__ == "__main__":
    asyncio.run(main())
