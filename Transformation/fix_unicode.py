import json
import os

INPUT_FILE = "data/processed/google_deduped.jsonl"
TEMP_FILE = "data/processed/google_deduped_fixed.jsonl"

def fix_unicode():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    print(f"Reading from {INPUT_FILE}...")
    
    count = 0
    with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
         open(TEMP_FILE, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            try:
                record = json.loads(line)
                # json.dumps with ensure_ascii=False writes actual unicode chars
                # instead of \uXXXX escapes.
                outfile.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
            except json.JSONDecodeError:
                continue
    
    # Replace original file
    os.replace(TEMP_FILE, INPUT_FILE)
    print(f"Fixed unicode for {count} records. File replaced.")

if __name__ == "__main__":
    fix_unicode()
