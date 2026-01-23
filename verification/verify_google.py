import aiohttp
import asyncio
import sqlite3
import pandas as pd
import os
import sys
import difflib
from pathlib import Path
import csv

# Add parent dir to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

DB_PATH = BASE_DIR / "data" / "books.db"
REPORT_PATH = BASE_DIR / "verification" / "google_comparison.csv"
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# Check API Key
API_KEY = os.environ.get("GOOGLEBOOKS_API_KEY")
if not API_KEY:
    print("WARNING: GOOGLEBOOKS_API_KEY not found in environment.")
    print("Running in limited unauthenticated mode (very slow/rate limited).")
else:
    print("Found GOOGLEBOOKS_API_KEY.")

def get_books_from_db(limit=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT local_id, title, author, description FROM books"
    if limit:
        query += f" ORDER BY RANDOM() LIMIT {limit}"
    else:
        query += " ORDER BY id ASC" # Predictable order for full run
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def calculate_similarity(a, b):
    if not a or not b: return 0.0
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def fetch_google_book(session, title, author):
    if not title: return None
    
    q = f"intitle:{title}"
    if author:
        q += f"+inauthor:{author}"
        
    params = {'q': q, 'maxResults': 1}
    if API_KEY:
        params['key'] = API_KEY
        
    try:
        async with session.get(GOOGLE_BOOKS_API, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                if 'items' in data:
                    return data['items'][0]['volumeInfo']
            elif resp.status == 429:
                return "RATE_LIMIT"
    except Exception as e:
        return None
    return None

async def verify_book(session, semaphore, row):
    local_id = row['local_id']
    local_title = row['title']
    local_author = row['author']
    local_desc = row['description']
    
    google_data = None
    retries = 3
    
    async with semaphore:
        # Retry logic for rate limits
        for _ in range(retries):
            google_data = await fetch_google_book(session, local_title, local_author)
            if google_data == "RATE_LIMIT":
                await asyncio.sleep(2) # Backoff
                continue
            break
            
    result = {
        'local_id': local_id,
        'local_title': local_title,
        'google_title': None,
        'title_similarity': 0.0,
        'google_has_desc': False,
        'local_has_desc': bool(local_desc),
        'match_found': False
    }
    
    if google_data and google_data != "RATE_LIMIT":
        g_title = google_data.get('title', '')
        g_desc = google_data.get('description', '')
        
        sim = calculate_similarity(local_title, g_title)
        
        result['google_title'] = g_title
        result['title_similarity'] = round(sim, 2)
        result['google_has_desc'] = bool(g_desc)
        result['match_found'] = True
        
    return result

async def run_verification(limit=5):
    print(f"Fetching books from DB (Limit={limit})...")
    df = get_books_from_db(limit)
    print(f"Verifying {len(df)} records against Google Books API...")
    
    # Higher concurrency if Key exists
    concurrency = 20 if API_KEY else 2
    semaphore = asyncio.Semaphore(concurrency)
    
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [verify_book(session, semaphore, row) for _, row in df.iterrows()]
        results = await asyncio.gather(*tasks)
        
    # Analyze
    verified_df = pd.DataFrame(results)
    
    print("\n--- Verification Results ---")
    print(verified_df[['local_id', 'local_title', 'google_title', 'title_similarity', 'match_found']].to_string(index=False))
    
    avg_sim = verified_df[verified_df['match_found']]['title_similarity'].mean()
    found_rate = verified_df['match_found'].mean()
    
    print(f"\nSummary:")
    print(f"Match Found Rate: {found_rate:.2%}")
    print(f"Avg Title Similarity (among matches): {avg_sim:.2f}")
    
    if limit is None or limit > 20:
        verified_df.to_csv(REPORT_PATH, index=False)
        print(f"\nFull report saved to {REPORT_PATH}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='Verify all records')
    args = parser.parse_args()
    
    limit = None if args.all else 5
    asyncio.run(run_verification(limit))
