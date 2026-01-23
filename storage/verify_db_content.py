import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "books.db"

def verify():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT local_id, title, author, genre, description, openlibrary_key FROM books WHERE description IS NOT NULL LIMIT 5"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print("--- Sample Enriched Books ---")
    print(df.to_string())
    
    # Check stats
    conn = sqlite3.connect(DB_PATH)
    count = pd.read_sql_query("SELECT COUNT(*) as total FROM books", conn)['total'][0]
    desc_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM books WHERE description IS NOT NULL", conn)['cnt'][0]
    genre_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM books WHERE genre IS NOT NULL AND genre != ''", conn)['cnt'][0]
    conn.close()
    
    print(f"\nTotal Records: {count}")
    print(f"With Description: {desc_count}")
    print(f"With Genre: {genre_count}")

if __name__ == "__main__":
    verify()
