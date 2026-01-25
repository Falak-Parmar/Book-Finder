import pandas as pd
import aiohttp
import asyncio
import json
import argparse
import os
from typing import Optional, Dict, Any, Set

MAX_CONCURRENT_REQUESTS = 3  # Reduced to avoid 429s
save_interval = 10

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = " ".join(text.split())
    text = text.strip(".,/:;")
    return text

async def search_google_books(session: aiohttp.ClientSession, title: str, author: str, retries=0) -> Optional[Dict[str, Any]]:
    base_url = "https://www.googleapis.com/books/v1/volumes"
    query = f"intitle:{title}"
    if author:
        query += f"+inauthor:{author}"
    
    params = {
        "q": query,
        "maxResults": 1,
        "langRestrict": "en"
    }
    
    backoff = 2 ** retries
    if retries > 5:
        print(f"Max retries reached for {title}")
        return None

    try:
        async with session.get(base_url, params=params) as response:
            if response.status == 429:
                wait_time = min(backoff * 1.5, 60) # Cap at 60s
                print(f"Rate limited. Waiting {wait_time}s... (Retry {retries+1})")
                await asyncio.sleep(wait_time)
                return await search_google_books(session, title, author, retries+1)
            
            response.raise_for_status()
            data = await response.json()
            
            if "items" in data and len(data["items"]) > 0:
                item = data["items"][0]
                volume_info = item.get("volumeInfo", {})
                
                return {
                    "google_id": item.get("id"),
                    "title": volume_info.get("title"),
                    "subtitle": volume_info.get("subtitle"),
                    "authors": volume_info.get("authors", []),
                    "description": volume_info.get("description"),
                    "published_date": volume_info.get("publishedDate"),
                    "page_count": volume_info.get("pageCount"),
                    "categories": volume_info.get("categories", []),
                    "average_rating": volume_info.get("averageRating"),
                    "thumbnail": volume_info.get("imageLinks", {}).get("thumbnail"),
                    "preview_link": volume_info.get("previewLink"),
                    "industry_identifiers": volume_info.get("industryIdentifiers", [])
                }
    except Exception as e:
        # print(f"Error searching for {title}: {e}")
        pass
    
    return None

async def process_book(session, row, semaphore):
    async with semaphore:
        original_title = clean_text(row.get("Title", ""))
        original_author = clean_text(row.get("Author/Editor", ""))
        
        if not original_title:
            return None

        google_data = await search_google_books(session, original_title, original_author)
        
        # Respect rate limits even with semaphore
        await asyncio.sleep(0.5) 
        
        return {
            "original_id": row.get("Acc. No."),
            "original_title": original_title,
            "original_author": original_author,
            "google_book_data": google_data,
            "found": google_data is not None
        }

def load_processed_ids(output_file: str) -> Set[Any]:
    processed_ids = set()
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    processed_ids.add(record["original_id"])
                except json.JSONDecodeError:
                    pass
    return processed_ids

async def main():
    parser = argparse.ArgumentParser(description="Ingest books from Google Books API Async")
    parser.add_argument("--limit", type=int, help="Limit number of books to process", default=None)
    parser.add_argument("--input", type=str, default="data/raw/Accession Register-Books.csv")
    parser.add_argument("--output", type=str, default="data/processed/books_enriched.jsonl")
    args = parser.parse_args()

    print(f"Reading from {args.input}...")
    try:
        df = pd.read_csv(args.input)
    except FileNotFoundError:
        print(f"Error: Input file {args.input} not found.")
        return

    # Load existing progress
    processed_ids = load_processed_ids(args.output)
    print(f"Found {len(processed_ids)} already processed records.")

    # Filter DF
    df_to_process = df[~df["Acc. No."].isin(processed_ids)]
    
    if args.limit:
        df_to_process = df_to_process.head(args.limit)
    
    print(f"Processing {len(df_to_process)} records...")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        results_buffer = []
        
        # Iterate and create tasks, but we want to stream results to file
        # effectively, so we might want to chunk the processing or use as_completed
        # For simplicity with the dataframe, we can create all tasks but that uses memory.
        # Let's use a batch approach to manage memory and file writing.
        
        batch_size = 20
        total_processed = 0
        
        # Convert to list of dicts for easier batching
        rows = df_to_process.to_dict('records')
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            batch_tasks = [process_book(session, row, semaphore) for row in batch]
            
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Write batch to file immediately
            with open(args.output, "a") as f:
                for res in batch_results:
                    if res:
                        f.write(json.dumps(res) + "\n")
            
            total_processed += len(batch_results)
            print(f"Processed {total_processed}/{len(rows)}...")

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
