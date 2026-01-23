import sqlite3
import os
from pathlib import Path

# Config
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "books.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create the table if it doesn't exist."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_id TEXT UNIQUE,
            title TEXT,
            author TEXT,
            isbn TEXT,
            description TEXT,
            genre TEXT,
            cover_image TEXT,
            openlibrary_key TEXT,
            publication_year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def upsert_book(book_data):
    """
    Insert a new book or update if local_id exists.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if exists
    local_id = str(book_data.get('local_id'))
    c.execute('SELECT id FROM books WHERE local_id = ?', (local_id,))
    data = c.fetchone()
    
    if data:
        # Update
        c.execute('''
            UPDATE books SET 
                title=?, author=?, isbn=?, description=?, genre=?, 
                cover_image=?, openlibrary_key=?, publication_year=?
            WHERE local_id=?
        ''', (
            book_data.get('title'),
            book_data.get('author'),
            book_data.get('isbn'),
            book_data.get('description'),
            book_data.get('genre'),
            book_data.get('cover_image'),
            book_data.get('openlibrary_key'),
            book_data.get('publication_year'),
            local_id
        ))
    else:
        # Insert
        c.execute('''
            INSERT INTO books (local_id, title, author, isbn, description, genre, cover_image, openlibrary_key, publication_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            local_id,
            book_data.get('title'),
            book_data.get('author'),
            book_data.get('isbn'),
            book_data.get('description'),
            book_data.get('genre'),
            book_data.get('cover_image'),
            book_data.get('openlibrary_key'),
            book_data.get('publication_year')
        ))
    
    conn.commit()
    conn.close()

def get_recent_books(limit=10):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM books ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_book_by_id(book_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def search_books(query=None, genre=None, limit=20):
    conn = get_db_connection()
    c = conn.cursor()
    
    sql = "SELECT * FROM books WHERE 1=1"
    params = []
    
    if query:
        # Simple LIKE search for now
        sql += " AND (title LIKE ? OR author LIKE ? OR description LIKE ?)"
        wildcard = f"%{query}%"
        params.extend([wildcard, wildcard, wildcard])
        
    if genre:
        sql += " AND genre LIKE ?"
        params.append(f"%{genre}%")
        
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    # Test initialization
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    init_db()
