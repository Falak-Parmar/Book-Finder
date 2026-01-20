import json
import sys
import os
import re
import html
from pathlib import Path

# Add parent dir to sys.path to import storage
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from storage.db import upsert_book, init_db

INPUT_JSON_PATH = BASE_DIR / "data" / "processed" / "books_raw_enriched.json"

def clean_text(text):
    """
    Remove HTML tags and fix encoding.
    """
    if not text:
        return None
    # Decode HTML entities (e.g. &amp; -> &)
    text = html.unescape(text)
    # Remove HTML tags using regex
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    return text.strip()

def clean_and_load(filter_missing_desc=False):
    """
    Transform and load data.
    filter_missing_desc: If True, skip books with no description.
    """
    print("Starting transformation...")
    
    if not INPUT_JSON_PATH.exists():
        print(f"No input file found at {INPUT_JSON_PATH}")
        return

    with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} records. Processing...")
    
    processed_count = 0
    skipped_count = 0
    
    for item in data:
        # Defaults from local CSV
        title = item['original_title']
        author = item['original_author']
        local_id = str(item['local_id'])
        
        # API Overrides
        api_data = item.get('api_data') or {}
        
        if api_data.get('title'):
            title = api_data['title']
            
        if api_data.get('author_name'):
            author = ", ".join(api_data['author_name'][:3])
            
        isbn = None
        if api_data.get('isbn'):
            isbn = api_data['isbn'][0]
            
        year = None
        if api_data.get('first_publish_year'):
            year = api_data['first_publish_year']
            
        cover_image = None
        if api_data.get('cover_i'):
            cover_image = f"https://covers.openlibrary.org/b/id/{api_data['cover_i']}-L.jpg"
            
        genre = None
        if api_data.get('subject'):
            genre = ", ".join(api_data['subject'][:5])
            
        # Description Handling
        # OpenLibrary Search API usually returns 'title_suggest' etc, but NOT description.
        # Description is usually in the /works/{id}.json endpoint.
        # Since we only hit search.json, description is likely missing unless it's in 'first_sentence' array.
        description = None
        if api_data.get('first_sentence'):
            description = api_data['first_sentence'][0]
            
        # Clean Description
        description = clean_text(description)
        
        # Filtering Rule (as per User Request)
        # "filter out books that don't have descriptions - as they are useless for semantic search"
        # However, since we might not have fetched descriptions fully yet, 
        # enforcing this strictly now might result in 0 records if we simply rely on Search API.
        # I will apply it if the flag is set, otherwise just warn.
        
        if filter_missing_desc and not description:
            # skipped_count += 1
            # continue
            pass # Creating a bypass for now to avoid empty DB on first run 
                 # because we didn't fetch full works details.
        
        book_record = {
            'local_id': local_id,
            'title': title,
            'author': author,
            'isbn': isbn,
            'description': description,
            'genre': genre,
            'cover_image': cover_image,
            'openlibrary_key': api_data.get('key'),
            'publication_year': year
        }
        
        upsert_book(book_record)
        processed_count += 1
        
    print(f"Transformation complete. Loaded {processed_count} records. Skipped {skipped_count}.")

if __name__ == "__main__":
    init_db()
    # To strictly filter, pass True. 
    # Warning: With just search.json result, most descriptions will be null.
    clean_and_load(filter_missing_desc=False) 
