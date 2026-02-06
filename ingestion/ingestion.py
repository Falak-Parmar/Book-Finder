import pandas as pd
import aiohttp
import asyncio
import json
import argparse
import os
from typing import Optional, Dict, Any, Set, List

# Configuration
MAX_CONCURRENT_REQUESTS = 3
SAVE_INTERVAL = 20
GOOGLE_VOLUME_API = "https://www.googleapis.com/books/v1/volumes/{}"

def clean_text(text):    # helper function to normalize text fields (titles, authors) before sending them to the API.
    if not isinstance(text, str):
        return ""
    text = " ".join(text.split())    #collapses multiple spaces into one and removes hidden newlines.
    text = text.strip(".,/:;")    #removes common punctuation.
    return text

# search Google Books API for a book by title and author
async def search_google_books(session: aiohttp.ClientSession, title: str, author: str, retries=0) -> Optional[Dict[str, Any]]:  
    base_url = "https://www.googleapis.com/books/v1/volumes"
    query = f"intitle:{title}"    # search for the book by title
    if author:
        query += f"+inauthor:{author}"    # search for the book by author
    
    params = {
        "q": query, # search query
        "maxResults": 1, # maximum number of results to return
        "langRestrict": "en" # restrict results to English
    }
    
    backoff = 2 ** retries    # exponential backoff
    if retries > 5:
        # print(f"Max retries reached for {title}")
        return None

    try:
        async with session.get(base_url, params=params) as response: 
            if response.status == 429:    # if too many requests
                wait_time = min(backoff * 1.5, 60)    
                # print(f"Rate limited. Waiting {wait_time}s... (Retry {retries+1})") 
                await asyncio.sleep(wait_time)    # wait for the backoff period
                return await search_google_books(session, title, author, retries+1)    # retry the request
            
            response.raise_for_status()    # raise an exception if the request was not successful
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
    except Exception: # catch any exceptions that may occur
        pass
    
    return None


async def fetch_isbns(session, google_id):
    if not google_id: return []
    
    url = GOOGLE_VOLUME_API.format(google_id)
    # No API Key used
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("volumeInfo", {}).get("industryIdentifiers", [])
            elif response.status == 429:
                return "RATE_LIMIT"    
    except Exception:
        pass
    return []


async def process_book(session, row, semaphore):
    async with semaphore:
        original_title = clean_text(row.get("Title", ""))
        original_author = clean_text(row.get("Author/Editor", ""))
        
        if not original_title:
            return None

        # 1. Search Google
        google_data = await search_google_books(session, original_title, original_author)    # await suspends this task until the API responds. Other tasks continue running meanwhile.
        
        await asyncio.sleep(0.5)    # pause for 0.5 seconds to avoid overwhelming the API
        
        return {
            "original_id": row.get("Acc. No."),
            "original_title": original_title,
            "original_author": original_author,
            "google_book_data": google_data,
            "found": google_data is not None
        }

# This function prevents duplicate processing.
def load_processed_ids(output_file: str) -> Set[Any]:
    processed_ids = set()
    if os.path.exists(output_file):    # if the file exists
        with open(output_file, "r", encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    processed_ids.add(str(record["original_id"]))
                except json.JSONDecodeError:
                    pass
    return processed_ids

async def main():
    parser = argparse.ArgumentParser(description="Ingest books from Google Books API Async")
    parser.add_argument("--limit", type=int, help="Limit number of books to process", default=None)
    # This allows the script to be run like: python ingestion.py --limit 100

    parser.add_argument("--input", type=str, default="data/raw/Accession Register-Books.csv")
    parser.add_argument("--output", type=str, default="data/processed/books_enriched.jsonl")
    # overall:  python ingestion.py --limit 100 --input my_books.csv --output out.jsonl
    args = parser.parse_args()

    print(f"Reading from {args.input}...", flush=True)
    try:
        df = pd.read_csv(args.input)
    except FileNotFoundError:
        print(f"Error: Input file {args.input} not found.")
        return

    processed_ids = load_processed_ids(args.output)
    print(f"Found {len(processed_ids)} already processed records.", flush=True)

    # Filter DF - Ensure string comparison
    df["Acc. No."] = df["Acc. No."].astype(str)  # Converts the Acc. No. column to string type
    df_to_process = df[~df["Acc. No."].isin(processed_ids)] # Selects only rows whose Acc. No. is not already processed
    
    if args.limit:
        df_to_process = df_to_process.head(args.limit) # Limits the number of books to process
    
    print(f"Processing {len(df_to_process)} records...", flush=True)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS) # Limits the number of concurrent requests   
    
    async with aiohttp.ClientSession() as session:
        rows = df_to_process.to_dict('records')
        total_processed = 0
        
        for i in range(0, len(rows), SAVE_INTERVAL):
            batch = rows[i:i+SAVE_INTERVAL]
            batch_tasks = [process_book(session, row, semaphore) for row in batch]
            
            batch_results = await asyncio.gather(*batch_tasks)
            
            with open(args.output, "a", encoding='utf-8') as f:
                for res in batch_results:
                    if res:
                        f.write(json.dumps(res) + "\n")
            
            total_processed += len(batch_results)
            print(f"Processed {total_processed}/{len(rows)} across all batches...", flush=True)

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
