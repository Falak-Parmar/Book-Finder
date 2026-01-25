import json
import os

INPUT_FILE = "data/processed/Google_cleaned.jsonl"
OUTPUT_FILE = "data/processed/google_deduped.jsonl"

def dedup_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    print(f"Reading from {INPUT_FILE}...")
    
    total_records = 0
    kept_records = 0
    duplicate_records = 0
    
    seen_ids = set()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            try:
                record = json.loads(line)
                total_records += 1
                
                g_id = record.get("google_id")
                
                # If no google_id, we can't dedup by it. 
                # Assuming we keep it if it has no ID (rare case based on prev steps)
                # But typically valid google records have IDs.
                # If g_id is None, let's treat it as distinct unless we want to remove?
                # User said "Dedup using Google_id". 
                # I'll check if g_id exists. If records have NO google_id, they are effectively distinct or 'unknown'.
                # But based on previous logic, all records here *have* google_data which should have an ID.
                
                if g_id and g_id in seen_ids:
                    duplicate_records += 1
                    continue
                
                if g_id:
                    seen_ids.add(g_id)
                
                outfile.write(line)
                kept_records += 1
                
            except json.JSONDecodeError:
                continue

    print(f"Deduplication complete.")
    print(f"Total processed: {total_records}")
    print(f"Duplicates removed: {duplicate_records}")
    print(f"Kept (google_deduped.jsonl): {kept_records}")

if __name__ == "__main__":
    dedup_data()
