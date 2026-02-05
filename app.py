import streamlit as st
import requests
import os
import sys
import html
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy import or_
from storage import db
from ml.embeddings import EmbeddingManager

# --- Configuration & Styling ---
st.set_page_config(
    page_title="Book Finder | Semantic Search",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium UI Theme
st.markdown("""
<style>
    :root {
        --primary-color: #6366f1;
        --secondary-color: #818cf8;
        --bg-color: #0f172a;
        --text-color: #f8fafc;
        --card-bg: rgba(30, 41, 59, 0.7);
    }
    
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 3rem;
    }
    
    .book-card {
        background: var(--card-bg);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        display: flex;
        gap: 1.5rem;
        backdrop-filter: blur(8px);
    }
    
    .book-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        border-color: var(--primary-color);
    }
    
    .book-thumbnail {
        width: 120px;
        height: 180px;
        border-radius: 8px;
        object-fit: cover;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .book-info {
        flex: 1;
    }
    
    .book-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 0.25rem;
    }
    
    .book-subtitle {
        font-size: 1rem;
        color: #94a3b8;
        margin-bottom: 1rem;
    }
    
    .book-author {
        font-size: 0.95rem;
        font-style: italic;
        color: #818cf8;
        margin-bottom: 1rem;
    }
    
    .book-description {
        font-size: 0.9rem;
        line-height: 1.5;
        color: #cbd5e1;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .category-tag {
        display: inline-block;
        background: rgba(99, 102, 241, 0.1);
        color: #818cf8;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 1rem;
    }

    /* Button Styling Overrides */
    div.stButton > button {
        background-color: var(--primary-color) !important;
        color: white !important;
        border: none !important;
        transition: all 0.3s ease !important;
        border-radius: 8px !important;
    }

    div.stButton > button:hover {
        background-color: var(--secondary-color) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* History chips specific styling */
    [data-testid="stHorizontalBlock"] div.stButton > button {
        font-size: 0.8rem;
        padding: 0.2rem 0.5rem;
        background-color: rgba(99, 102, 241, 0.2) !important;
        border: 1px solid rgba(99, 102, 241, 0.5) !important;
    }

    [data-testid="stHorizontalBlock"] div.stButton > button:hover {
        background-color: var(--primary-color) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Logic ---

PAGE_SIZE = 15
DISTANCE_THRESHOLD = 0.7  # Lower distance means higher similarity

@st.cache_resource(show_spinner=False)
def get_embedding_manager():
    return EmbeddingManager()

def get_db():
    return db.SessionLocal()

@st.dialog("Book Details", width="large")
def show_book_details(book):
    title = html.escape(book.title) if book.title else "Untitled"
    subtitle = html.escape(book.subtitle) if book.subtitle else ""
    authors = html.escape(book.authors) if book.authors else "Unknown Author"
    description = html.escape(book.description) if book.description else "No description available."
    thumbnail = book.thumbnail if book.thumbnail else "https://via.placeholder.com/120x180?text=No+Cover"
    categories = html.escape(book.categories) if book.categories else "General"
    isbn = book.isbn_13 if book.isbn_13 else "N/A"
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(thumbnail, use_container_width=True)
    with col2:
        st.markdown(f"### {title}")
        if subtitle:
            st.markdown(f"**{subtitle}**")
        st.markdown(f"*by {authors}*")
        st.markdown(f"**Categories:** {categories}")
        st.markdown(f"**ISBN-13:** {isbn}")
        st.divider()
        st.markdown("#### Description")
        st.write(description)

def perform_semantic_search(query, manager, session, n_results=300, threshold=DISTANCE_THRESHOLD):
    results = manager.search(query, n_results=n_results)
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    if not ids:
        return []
        
    # Filter by threshold
    filtered_ids = [idx for idx, dist in zip(ids, distances) if dist <= threshold]
    
    if not filtered_ids:
        return []
        
    books = session.query(db.Book).filter(
        or_(
            db.Book.isbn_13.in_(filtered_ids),
            db.Book.google_id.in_(filtered_ids)
        )
    ).all()
    
    # Sort by relevance (Chromadb order)
    id_to_index = {idx: i for i, idx in enumerate(filtered_ids)}
    books.sort(key=lambda b: id_to_index.get(b.isbn_13) if b.isbn_13 in id_to_index else id_to_index.get(b.google_id, 999))
    return books

def perform_keyword_search(query, session):
    search_term = f"%{query}%"
    query_obj = session.query(db.Book).filter(
        or_(
            db.Book.title.ilike(search_term),
            db.Book.authors.ilike(search_term),
            db.Book.isbn_13 == query
        )
    )
    total = query_obj.count()
    return query_obj.all(), total

# --- Session State ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'total_results' not in st.session_state:
    st.session_state.total_results = 0
if 'current_results' not in st.session_state:
    st.session_state.current_results = []
if 'last_final_query' not in st.session_state:
    st.session_state.last_final_query = ""

# --- UI ---

st.markdown('<div class="main-header">Book Finder</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Discover your next read through meaning, not just keywords.</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://www.daiict.ac.in/sites/default/files/inline-images/Dhirubhai-Ambani-University-new-logo.jpg", use_container_width=True)

# Main Search Area
query_input = st.text_input(
    "What are you looking for?", 
    placeholder="Search for a book, theme, or topic...",
    help="Type your query and press Enter. Click history chips below to reuse previous searches."
)

if st.session_state.history:
    st.markdown("##### Recent Searches")
    hist_cols = st.columns(min(len(st.session_state.history), 5))
    for i, h_query in enumerate(reversed(st.session_state.history[-5:])):
        if hist_cols[i].button(h_query, key=f"hist_chip_{i}", use_container_width=True):
            st.session_state.active_query = h_query
            st.session_state.page = 1  # Reset to page 1 on new search
            st.rerun()

final_query = st.session_state.get('active_query', query_input)

# Detect if the query has changed to reset page
if final_query != st.session_state.last_final_query:
    st.session_state.page = 1
    st.session_state.last_final_query = final_query

if final_query:
    if 'active_query' in st.session_state:
        del st.session_state['active_query']
        
    if final_query and final_query not in st.session_state.history:
        st.session_state.history.append(final_query)
        if len(st.session_state.history) > 10:
            st.session_state.history.pop(0)

    manager = get_embedding_manager()
    session = get_db()
    
    # Only perform search if it's a new query OR page reset
    # (Actually, in Streamlit, it usually re-renders. We can optimize but let's keep it simple first)
    with st.spinner("Finding the best matches..."):
        # For Semantic Search, we fetch a large pool and paginate locally
        # For Keyword Search, we fetch all and paginate locally (given the DB is small enough)
        # In a real app, we'd use offset/limit on the DB.
        if "active_query_results" not in st.session_state or st.session_state.last_final_query != final_query:
            if "Semantic" in "Semantic Search 🧠":
                results = perform_semantic_search(final_query, manager, session)
                total = len(results)
            else:
                results, total = perform_keyword_search(final_query, session)
            
            st.session_state.active_query_results = results
            st.session_state.total_results = total
    
    results = st.session_state.active_query_results
    total = st.session_state.total_results
    
    if not results:
        st.warning("No books found matching your query.")
    else:
        # Paging math
        start_idx = (st.session_state.page - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total)
        page_results = results[start_idx:end_idx]
        
        st.info(f"Showing {start_idx + 1} to {end_idx} of {total} results for '{final_query}'")
        
        for i, book in enumerate(page_results):
            title = html.escape(book.title) if book.title else "Untitled"
            subtitle = html.escape(book.subtitle) if book.subtitle else ""
            authors = html.escape(book.authors) if book.authors else "Unknown Author"
            description_short = html.escape(book.description[:250] + "...") if book.description and len(book.description) > 250 else html.escape(book.description) if book.description else "No description available."
            thumbnail = book.thumbnail if book.thumbnail else "https://via.placeholder.com/120x180?text=No+Cover"
            categories = html.escape(book.categories.split(",")[0]) if book.categories else "General"
            
            card_col1, card_col2 = st.columns([5, 1])
            with card_col1:
                book_html = (
                    f'<div class="book-card">'
                    f'<img src="{thumbnail}" class="book-thumbnail" onerror="this.src=\'https://via.placeholder.com/120x180?text=No+Cover\'">'
                    f'<div class="book-info">'
                    f'<div class="book-title">{title}</div>'
                    f'{"<div class=\'book-subtitle\'>" + subtitle + "</div>" if subtitle else ""}'
                    f'<div class="book-author">by {authors}</div>'
                    f'<div class="book-description">{description_short}</div>'
                    f'<div class="category-tag">{categories}</div>'
                    f'</div></div>'
                )
                st.markdown(book_html, unsafe_allow_html=True)
            with card_col2:
                st.write("") # Spacer
                st.write("") # Spacer
                if st.button("Details", key=f"details_{book.isbn_13}_{i}", use_container_width=True):
                    show_book_details(book)
        
        # Pagination Controls
        st.divider()
        col_prev, col_mid, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.session_state.page > 1:
                if st.button("← Previous Page", use_container_width=True):
                    st.session_state.page -= 1
                    st.rerun()
        with col_mid:
            num_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
            st.markdown(f"<p style='text-align: center;'>Page <b>{st.session_state.page}</b> of {num_pages}</p>", unsafe_allow_html=True)
        with col_next:
            if end_idx < total:
                if st.button("Next Page →", use_container_width=True):
                    st.session_state.page += 1
                    st.rerun()
    
    session.close()
else:
    st.write("---")
    st.markdown("""
    ### Popular Searches
    - *Modern machine learning techniques*
    - *Classic English literature*
    - *Books about the history of India*
    - *Introduction to quantum physics*
    """)
