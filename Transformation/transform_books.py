import csv
import json
import os
import datetime

INPUT_JSON = r"data/processed/books_with_isbn.jsonl"
INPUT_CSV = r"data/raw/Accession Register-Books.csv"
OUTPUT_FILE = r"data/processed/Google_cleaned.jsonl"
LOG_FILE = r"logs/project_log.md"

def load_csv_metadata():
    print(f"Loading metadata from {INPUT_CSV}...")
    metadata_map = {}
    try:
        with open(INPUT_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                acc_no = row.get("Acc. No.", "").strip()
                if acc_no:
                    metadata_map[str(acc_no)] = {
                        "edition_volume": row.get("Ed./Vol.", "").strip(),
                        "publisher_info": row.get("Place & Publisher", "").strip(),
                        "book_no": row.get("Class No./Book No.", "").strip()
                    }
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return metadata_map

def clean_data():
    if not os.path.exists(INPUT_JSON):
        print(f"Error: Input file {INPUT_JSON} not found.")
        return

    csv_metadata = load_csv_metadata()
    print(f"Reading from {INPUT_JSON}...")
    
    total_records = 0
    kept_records = 0
    removed_no_isbn = 0
    removed_duplicate = 0
    
    seen_isbns = set()
    
    with open(INPUT_JSON, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            try:
                record = json.loads(line)
                total_records += 1
                
                google_data = record.get("google_book_data", {})
                if not google_data:
                    removed_no_isbn += 1
                    continue

                identifiers = google_data.get("industry_identifiers", [])
                
                # Extract ISBNs (Just for inclusion, not filtering)
                isbn_13 = None
                isbn_10 = None
                for ident in identifiers:
                    if ident['type'] == 'ISBN_13':
                        isbn_13 = ident['identifier']
                    elif ident['type'] == 'ISBN_10':
                        isbn_10 = ident['identifier']
                
                # 3. Merge CSV Data
                # Get original_id to link
                original_id = str(record.get("original_id", "")).strip()
                csv_info = csv_metadata.get(original_id, {})
                
                # 4. Construct Final Record (Explicitly excluding removed fields)
                # User asked to discard: original_title, original_author, original_id, found, average_rating
                
                final_record = {
                    "title": google_data.get("title"),
                    "subtitle": google_data.get("subtitle"),
                    "authors": google_data.get("authors", []), # Use Google authors
                    "description": google_data.get("description"),
                    "isbn_13": isbn_13,
                    "isbn_10": isbn_10,
                    "categories": google_data.get("categories", []),
                    "page_count": google_data.get("page_count"),
                    "published_date": google_data.get("published_date"),
                    "thumbnail": google_data.get("thumbnail"),
                    "preview_link": google_data.get("preview_link"),
                    "google_id": google_data.get("google_id"),
                    
                    # Merged Fields
                    "edition_volume": csv_info.get("edition_volume"),
                    "publisher_info": csv_info.get("publisher_info"),
                    "book_no": csv_info.get("book_no")
                }

                outfile.write(json.dumps(final_record) + "\n")
                kept_records += 1
                
            except json.JSONDecodeError:
                continue

    print(f"Processing complete.")
    print(f"Total processed: {total_records}")
    print(f"Removed (No ISBN): {removed_no_isbn}")
    print(f"Removed (Duplicate): {removed_duplicate}")
    print(f"Kept (Google_cleaned.jsonl): {kept_records}")
    
    log_interaction(total_records, removed_no_isbn + removed_duplicate, kept_records)

def log_interaction(total, removed, kept):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
## Data Transformation - {timestamp}
- **Task**: Create `Google_cleaned.jsonl`
- **Logic**: Merge CSV fields + Filter ISBN + Dedup + Select Columns.
- **Input File**: `{INPUT_JSON}`
- **Output File**: `{OUTPUT_FILE}`
- **Stats**:
  - Total scanned: {total}
  - Removed (No ISBN/Dup): {removed}
  - Kept: {kept}
"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding='utf-8') as f:
        f.write(log_entry)


if __name__ == "__main__":
    clean_data()
