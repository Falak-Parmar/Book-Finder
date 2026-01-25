import asyncio
import aiohttp
import json
import os
import argparse
from typing import Optional, Dict, Any, List

INPUT_FILE = "data/processed/books_cleaned.jsonl"
OUTPUT_FILE = "data/processed/books_cleaned_with_isbn.jsonl"
GOOGLE_VOLUME_API = "https://www.googleapis.com/books/v1/volumes/{}"
MAX_CONCURRENT_REQUESTS = 50 # High speed per user request

# Force Unauthenticated Mode to bypass quota
API_KEY = None 

async def fetch_isbns(session, google_id):
    if not google_id: return []
    
    url = GOOGLE_VOLUME_API.format(google_id)
    params = {}
    if API_KEY:
        params['key'] = API_KEY
        
    try:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("volumeInfo", {}).get("industryIdentifiers", [])
            elif response.status == 429:
                return "RATE_LIMIT"
    except Exception:
        pass
    return []

async def process_record(session, semaphore, line):
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None

    google_data = record.get("google_book_data")
    if not google_data:
        return record
        
    google_id = google_data.get("google_id")
    if not google_id:
        return record

    async with semaphore:
        retries = 3
        isbns = []
        for _ in range(retries):
            res = await fetch_isbns(session, google_id)
            if res == "RATE_LIMIT":
                await asyncio.sleep(2.0)
                continue
            isbns = res
            break
            
        if isbns:
            record["google_book_data"]["industry_identifiers"] = isbns
            
    return record

async def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file {INPUT_FILE} not found.")
        return

    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # RESUME LOGIC
    processed_ids = set()
    if os.path.exists(OUTPUT_FILE):
        print(f"Checking existing output for resume: {OUTPUT_FILE}")
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    # Track using original_id to match input
                    if "original_id" in rec:
                        processed_ids.add(str(rec["original_id"]))
                except:
                    pass
        print(f"Resuming... Found {len(processed_ids)} already processed records.")

    # Filter input
    lines_to_process = []
    for line in lines:
        try:
            r = json.loads(line)
            if str(r.get("original_id")) not in processed_ids:
                lines_to_process.append(line)
        except:
            pass
            
    if not lines_to_process:
        print("All records already processed.")
        return
        
    print(f"Enriching {len(lines_to_process)} records with ISBNs...")
    if API_KEY:
        print("Using GOOGLEBOOKS_API_KEY.")
    else:
        print("WARNING: No API Key found.")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    enriched_count = 0
    batch_size = 50 
    
    # APPEND mode
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as outfile:
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(lines_to_process), batch_size):
                batch = lines_to_process[i:i+batch_size]
                tasks = [process_record(session, semaphore, line) for line in batch]
                
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        outfile.write(json.dumps(res) + "\n")
                        if res.get("google_book_data", {}).get("industry_identifiers"):
                            enriched_count += 1
                            
                total_done = len(processed_ids) + min(i+batch_size, len(lines_to_process))
                print(f"Processed {total_done}/{len(lines)}... (New Enriched: {enriched_count})")

    print(f"Done. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
