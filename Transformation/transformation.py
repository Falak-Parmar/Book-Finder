import csv
import json
import os
import datetime

# --- Configuration ---
INPUT_JSON_ENRICHED = r"data/processed/books_enriched.jsonl" # Output from ingestion
INPUT_CSV = r"data/raw/Accession Register-Books.csv"
OUTPUT_TRANSFORMED = r"data/processed/Google_cleaned.jsonl"
OUTPUT_DEDUPED = r"data/processed/google_deduped.jsonl"
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

def transform_step():
    print("\n--- Step 1: Transforming & Merging ---")
    if not os.path.exists(INPUT_JSON_ENRICHED):
        print(f"Error: Input file {INPUT_JSON_ENRICHED} not found.")
        return False

    csv_metadata = load_csv_metadata()
    print(f"Reading from {INPUT_JSON_ENRICHED}...")
    
    total_records = 0
    kept_records = 0
    removed_no_isbn = 0 # Actually just 'no google data' now
    
    with open(INPUT_JSON_ENRICHED, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_TRANSFORMED, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            try:
                record = json.loads(line)
                total_records += 1
                
                google_data = record.get("google_book_data", {})
                if not google_data:
                    removed_no_isbn += 1
                    continue

                identifiers = google_data.get("industry_identifiers", [])
                
                isbn_13 = None
                isbn_10 = None
                for ident in identifiers:
                    if ident['type'] == 'ISBN_13':
                        isbn_13 = ident['identifier']
                    elif ident['type'] == 'ISBN_10':
                        isbn_10 = ident['identifier']
                
                original_id = str(record.get("original_id", "")).strip()
                csv_info = csv_metadata.get(original_id, {})
                
                final_record = {
                    "title": google_data.get("title"),
                    "subtitle": google_data.get("subtitle"),
                    "authors": google_data.get("authors", []),
                    "description": google_data.get("description"),
                    "isbn_13": isbn_13,
                    "isbn_10": isbn_10,
                    "categories": google_data.get("categories", []),
                    "page_count": google_data.get("page_count"),
                    "published_date": google_data.get("published_date"),
                    "thumbnail": google_data.get("thumbnail"),
                    "preview_link": google_data.get("preview_link"),
                    "google_id": google_data.get("google_id"),
                    
                    "edition_volume": csv_info.get("edition_volume"),
                    "publisher_info": csv_info.get("publisher_info"),
                    "book_no": csv_info.get("book_no")
                }

                outfile.write(json.dumps(final_record) + "\n")
                kept_records += 1
                
            except json.JSONDecodeError:
                continue

    print(f"Transformation processed: {total_records}")
    print(f"Kept: {kept_records}")
    return True

def dedup_step():
    print("\n--- Step 2: Deduplication ---")
    if not os.path.exists(OUTPUT_TRANSFORMED):
        print(f"Error: {OUTPUT_TRANSFORMED} not found.")
        return

    total_records = 0
    kept_records = 0
    duplicate_records = 0
    seen_google_ids = set()
    seen_isbns = set()
    
    with open(OUTPUT_TRANSFORMED, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_DEDUPED, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            try:
                record = json.loads(line)
                total_records += 1
                g_id = record.get("google_id")
                isbn = record.get("isbn_13")
                
                is_duplicate = False
                if g_id and g_id in seen_google_ids:
                    is_duplicate = True
                elif isbn and isbn in seen_isbns:
                    is_duplicate = True
                
                if is_duplicate:
                    duplicate_records += 1
                    continue
                
                if g_id:
                    seen_google_ids.add(g_id)
                if isbn:
                    seen_isbns.add(isbn)
                
                # unicode fix inline: ensure_ascii=False
                outfile.write(json.dumps(record, ensure_ascii=False) + "\n")
                kept_records += 1
            except json.JSONDecodeError:
                continue

    print(f"Deduplication processed: {total_records}")
    print(f"Duplicates removed: {duplicate_records}")
    print(f"Final Count (google_deduped.jsonl): {kept_records}")

def main():
    if transform_step():
        dedup_step()
    print("\nTransformation Pipeline Complete.")

if __name__ == "__main__":
    main()
