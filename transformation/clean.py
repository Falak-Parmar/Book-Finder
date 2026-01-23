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
    
def clean_and_load(filter_missing_desc=False):
    """
    Transform and load data.
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
        title = item.get('original_title', '')
        author = item.get('original_author', '')
        local_id = str(item.get('local_id', ''))
        
        api_data = item.get('api_data') or {}
        source = item.get('source', 'openlibrary') # 'openalex' or 'openlibrary'
        
        # --- FIELDS EXTRACTION ---
        isbn = None
        year = None
        cover_image = None
        genre = None
        description = None
        key = None
        
        if source == 'openalex':
            # OpenAlex Logic
            if api_data.get('title'):
                title = api_data['title']
                
            # Authors: extract from simple authorships list (pruned or raw)
            if 'authorships' in api_data:
                auth_list = []
                for auth in api_data['authorships']:
                    # Direct check if it's the simplified dict or full object
                    if 'display_name' in auth: # Simplified
                        auth_list.append(auth['display_name'])
                    elif 'author' in auth: # Full
                        auth_list.append(auth['author'].get('display_name', ''))
                if auth_list:
                    author = ", ".join(auth_list[:3])
            
            # Year
            year = api_data.get('publication_year')
            
            # Key (Using OpenAlex ID)
            key = api_data.get('id')
            
            # Valid Description (from rebuilt abstract)
            description = item.get('openalex_abstract')
            
            # Cover Image (OpenAlex doesn't always have covers directly easily accessible as URL?
            # actually it's sparse. We might keep it None or try to find an OpenAccess PDF thumbnail?)
            # For now, OpenAlex doesn't provide cover images like OpenLibrary.
            cover_image = None 
            
            # Genre/Topics - Extract from Concepts
            concepts = api_data.get('concepts', [])
            if concepts:
                # Concepts are usually sorted by score? Or we can just take first few.
                # OpenAlex sorts them by score descending usually.
                genre_list = [c.get('display_name') for c in concepts[:5]]
                genre = ", ".join(genre_list)
            
        else:
            # Fallback OpenLibrary Logic
            work_details = item.get('work_details') or {}
            
            if api_data.get('title'):
                title = api_data['title']
            if api_data.get('author_name'):
                author = ", ".join(api_data['author_name'][:3])
            if api_data.get('isbn'):
                isbn = api_data['isbn'][0]
            if api_data.get('first_publish_year'):
                year = api_data['first_publish_year']
            if api_data.get('cover_i'):
                cover_image = f"https://covers.openlibrary.org/b/id/{api_data['cover_i']}-L.jpg"
            if api_data.get('subject'):
                genre = ", ".join(api_data['subject'][:5])
            
            # Description
            raw_desc = work_details.get('description')
            if raw_desc:
                if isinstance(raw_desc, str):
                    description = raw_desc
                elif isinstance(raw_desc, dict) and 'value' in raw_desc:
                    description = raw_desc['value']
            if not description and api_data.get('first_sentence'):
                description = api_data['first_sentence'][0]
            
            key = api_data.get('key')

        # Formatting
        description = clean_text(description)
        
        if filter_missing_desc and not description:
            skipped_count += 1
            continue
        
        book_record = {
            'local_id': local_id,
            'title': title,
            'author': author,
            'isbn': isbn,
            'description': description,
            'genre': genre, # might be null for OpenAlex
            'cover_image': cover_image,
            'openlibrary_key': key, # Storing OpenAlex ID here effectively
            'publication_year': year
        }
        
        upsert_book(book_record)
        processed_count += 1
        
    print(f"Transformation complete. Loaded {processed_count} records. Skipped {skipped_count}.")

if __name__ == "__main__":
    init_db()
    # To strictly filter, pass True. 
    clean_and_load(filter_missing_desc=False) 
