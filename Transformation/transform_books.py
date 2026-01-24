import json
import os
import datetime

INPUT_FILE = r"data/processed/books_enriched.jsonl"
OUTPUT_FILE = r"data/processed/books_cleaned.jsonl"
LOG_FILE = r"logs/project_log.md"

def clean_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    print(f"Reading from {INPUT_FILE}...")
    
    total_records = 0
    kept_records = 0
    removed_records = 0
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            try:
                record = json.loads(line)
                total_records += 1
                
                # Filter logic:
                # Remove if "found" is False
                if not record.get("found", False):
                    removed_records += 1
                    continue
                
                # Remove if "categories" is inclusive empty AND "description" is null (None)
                # The user specified: remove if (categories == [] AND description == null)
                
                categories = record.get("google_book_data", {}).get("categories", [])
                description = record.get("google_book_data", {}).get("description")
                
                # Handle cases where google_book_data might be missing but found is True (shouldn't happen based on logic but good safety)
                if record.get("found") and record.get("google_book_data") is None:
                     # If found is true but no data, likely an issue, but let's stick to strict logic. 
                     # If google_book_data is missing, categories is [] and description is None.
                     pass 

                if (categories == []) and (description is None):
                    removed_records += 1
                    continue
                
                # If we passed filters, write to output
                outfile.write(json.dumps(record) + "\n")
                kept_records += 1
                
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line[:50]}...")
                continue

    print(f"Processing complete.")
    print(f"Total records: {total_records}")
    print(f"Removed records: {removed_records}")
    print(f"Kept records: {kept_records}")
    
    log_interaction(total_records, removed_records, kept_records)

def log_interaction(total, removed, kept):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
## Data Transformation - {timestamp}
- **Task**: Clean `books_enriched.jsonl`
- **Logic**: Removed entries where `found` is False OR (`categories` is [] AND `description` is null).
- **Input File**: `{INPUT_FILE}`
- **Output File**: `{OUTPUT_FILE}`
- **Stats**:
  - Total Records: {total}
  - Removed Records: {removed}
  - Kept Records: {kept}
"""
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    with open(LOG_FILE, "a", encoding='utf-8') as f:
        f.write(log_entry)
    print(f"Log updated at {LOG_FILE}")

if __name__ == "__main__":
    clean_data()
