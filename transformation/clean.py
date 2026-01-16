import json
import sys
import os
from pathlib import Path

# Add parent dir to sys.path to import storage
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from storage.db import upsert_book, init_db

INPUT_JSON_PATH = BASE_DIR / "data" / "processed" / "books_raw_enriched.json"

def clean_and_load():
    print("Starting transformation...")
    
    if not INPUT_JSON_PATH.exists():
        print(f"No input file found at {INPUT_JSON_PATH}")
        return

    with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} records. Processing...")
    
    for item in data:
        # Defaults from local CSV
        title = item['original_title']
        author = item['original_author']
        local_id = item['local_id']
        
        # API Overrides
        api_data = item.get('api_data') or {}
        
        # If API found a title, use it (usually cleaner)
        if api_data.get('title'):
            title = api_data['title']
            
        # Get Authors
        if api_data.get('author_name'):
            author = ", ".join(api_data['author_name'][:3]) # Top 3 authors
            
        # ISBN (first one)
        isbn = None
        if api_data.get('isbn'):
            isbn = api_data['isbn'][0]
            
        # Year
        year = None
        if api_data.get('first_publish_year'):
            year = api_data['first_publish_year']
            
        # Cover
        cover_image = None
        if api_data.get('cover_i'):
            cover_image = f"https://covers.openlibrary.org/b/id/{api_data['cover_i']}-L.jpg"
            
        # Genre/Subject
        genre = None
        if api_data.get('subject'):
            genre = ", ".join(api_data['subject'][:5]) # Top 5
            
        # Description (Search API usually doesn't have it, but we handle if present)
        description = None
        # Logic to strip HTML would go here if we had description
        
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
        
    print("Transformation and Loading complete.")

if __name__ == "__main__":
    init_db() # Ensure DB exists
    clean_and_load()
