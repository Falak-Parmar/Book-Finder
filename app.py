import streamlit as st
import requests
import os
import sys
import html
from sqlalchemy.orm import Session

# Version stamp for deployment verification
APP_VERSION = "v1.2-STABLE"

# Add project root to sys.path
sys.path.append(os.getcwd())

API_URL = os.environ.get("API_URL")

# Conditional imports to allow running without local DB/ML deps
try:
    from sqlalchemy import or_
    from storage import db
    from ml.embeddings import EmbeddingManager
    HAS_LOCAL_DEPS = True
except ImportError:
    HAS_LOCAL_DEPS = False

class BookWrapper:
    """A simple wrapper to allow dictionary access via dots (compatible with SQLAlchemy model usage)"""
    def __init__(self, data):
        self.__dict__.update(data)

# --- Configuration & Styling ---
st.set_page_config(
    page_title="Book Finder | Semantic Search",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Theme Configuration ---
if 'theme_choice' not in st.session_state:
    st.session_state.theme_choice = "Dark High Contrast"

themes = {
    "Light High Contrast": {
        "bg_color": "#ffffff",
        "text_color": "#0e1116",
        "primary_color": "#0969da",
        "secondary_color": "#0550ae",
        "card_bg": "#ffffff",
        "border_color": "#1b1f24",
        "muted_text": "#4b535d",
        "tag_bg": "rgba(9, 105, 218, 0.1)",
        "tag_text": "#0969da",
        "header_gradient": "linear-gradient(90deg, #0969da, #1f2328)"
    },
    "Dark High Contrast": {
        "bg_color": "#010409",
        "text_color": "#ffffff",
        "primary_color": "#4493f8",
        "secondary_color": "#1f6feb",
        "card_bg": "#0d1117",
        "border_color": "#30363d",
        "muted_text": "#8b949e",
        "tag_bg": "rgba(68, 147, 248, 0.1)",
        "tag_text": "#4493f8",
        "header_gradient": "linear-gradient(90deg, #4493f8, #ffffff)"
    }
}

t = themes[st.session_state.theme_choice]

st.markdown(f"""
<style>
    :root {{
        --primary-color: {t['primary_color']};
        --secondary-color: {t['secondary_color']};
        --bg-color: {t['bg_color']};
        --text-color: {t['text_color']};
        --card-bg: {t['card_bg']};
        --border-color: {t['border_color']};
        --muted-text: {t['muted_text']};
        --tag-bg: {t['tag_bg']};
        --tag-text: {t['tag_text']};
    }}
    
    .stApp {{
        background-color: var(--bg-color);
        color: var(--text-color);
    }}

    /* Fix for white header spill and toolbar */
    header[data-testid="stHeader"], [data-testid="stToolbar"] {{
        background-color: var(--bg-color) !important;
        background: var(--bg-color) !important;
    }}

    /* Remove the colorful line at the top */
    [data-testid="stDecoration"] {{
        display: none;
    }}

    /* Global input styling */
    .stTextInput input, .stSelectbox [data-baseweb="select"], .stSelectbox [role="button"] {{
        background-color: var(--card-bg) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
    }}
    
    /* Ensure markdown lists and text use the text-color variable */
    .stMarkdown, .stMarkdown p, .stMarkdown li {{
        color: var(--text-color) !important;
    }}
    
    /* ULTRA-AGGRESSIVE CSS FOR SIDEBAR ARROW */
    [data-testid="collapsedControl"] {{
        color: var(--text-color) !important;
        fill: var(--text-color) !important;
    }}
    [data-testid="collapsedControl"] svg {{
        fill: currentColor !important;
        width: 32px !important;
        height: 32px !important;
        filter: brightness(0) invert(1) !important; /* Force white for visibility */
    }}
    section[data-testid="stSidebar"] button svg {{
        fill: white !important;
    }}
    
    /* VERY aggressive fix for sidebar arrows and header icons */
    [data-testid="collapsedControl"] svg,
    [data-testid="stHeader"] svg,
    [data-testid="stSidebarNav"] svg,
    button[kind="header"] svg,
    .st-emotion-cache-6qob1r {{
        fill: white !important;
        color: white !important;
        filter: brightness(0) invert(1) !important;
    }}
    
    /* Fix for sidebar menu arrow visibility in dark mode */
    [data-testid="collapsedControl"] svg, 
    [data-testid="stSidebarNav"] svg,
    button[kind="header"] svg,
    .st-emotion-cache-6qob1r {{
        fill: var(--text-color) !important;
        color: var(--text-color) !important;
    }}
    
    /* Force visibility of the expand/collapse icon */
    [data-testid="stSidebar"] svg, [data-testid="collapsedControl"] svg {{
        background-color: transparent !important;
        stroke: var(--text-color) !important;
    }}
    
    /* Force white color for all sidebar buttons and icons */
    [data-testid="stSidebar"] button, 
    [data-testid="stSidebar"] svg,
    [data-testid="collapsedControl"] svg {{
        fill: white !important;
        color: white !important;
        opacity: 1 !important;
    }}

    .main-header {{
        font-size: 3rem;
        font-weight: 800;
        background: {t['header_gradient']};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }}
    
    .sub-header {{
        font-size: 1.2rem;
        color: var(--muted-text);
        text-align: center;
        margin-bottom: 3rem;
    }}
    
    .book-card {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: flex;
        gap: 1.5rem;
    }}
    
    .book-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
    }}
    
    .book-thumbnail {{
        width: 120px;
        height: 180px;
        border-radius: 4px;
        object-fit: cover;
        border: 1px solid var(--border-color);
    }}
    
    .book-info {{
        flex: 1;
    }}
    
    .book-title {{
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--text-color);
        margin-bottom: 0.25rem;
    }}
    
    .book-subtitle {{
        font-size: 1rem;
        color: var(--muted-text);
        margin-bottom: 1rem;
    }}
    
    .book-author {{
        font-size: 0.95rem;
        color: var(--primary-color);
        margin-bottom: 1rem;
    }}
    
    .book-description {{
        font-size: 0.9rem;
        line-height: 1.5;
        color: var(--text-color);
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        opacity: 0.9;
    }}
    
    .category-tag {{
        display: inline-block;
        background: var(--tag-bg);
        color: var(--tag-text);
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 1rem;
        border: 1px solid var(--tag-bg);
    }}

    /* Button Styling Overrides */
    div.stButton > button {{
        background-color: var(--primary-color) !important;
        color: white !important;
        border: 1px solid var(--border-color) !important;
        transition: all 0.2s ease !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }}

    div.stButton > button:hover {{
        background-color: var(--secondary-color) !important;
        border-color: var(--primary-color) !important;
    }}

    /* History chips specific styling */
    [data-testid="stHorizontalBlock"] div.stButton > button {{
        font-size: 0.8rem;
        padding: 0.2rem 0.5rem;
        background-color: var(--card-bg) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
    }}

    [data-testid="stHorizontalBlock"] div.stButton > button:hover {{
        background-color: var(--tag-bg) !important;
        color: var(--tag-text) !important;
        border-color: var(--primary-color) !important;
    }}

    /* Muted search info */
    .search-info {{
        color: var(--muted-text);
        margin-bottom: 1.5rem;
        font-size: 0.9rem;
    }}

    /* Sidebar adjustments */
    section[data-testid="stSidebar"] {{
        background-color: var(--card-bg);
        border-right: 1px solid var(--border-color);
    }}
</style>
""", unsafe_allow_html=True)

# --- Logic ---

PAGE_SIZE = 15
DISTANCE_THRESHOLD = 0.7  # Lower distance means higher similarity

@st.cache_resource(show_spinner=False)
def get_embedding_manager():
    if API_URL:
        return None
    return EmbeddingManager()

@st.cache_data(show_spinner=False)
def _get_db_session():
    if API_URL:
        return None
    return db.SessionLocal()

def get_db():
    if API_URL:
        return None
    return db.SessionLocal()

def get_api_health():
    """Check if the backend is actually ready"""
    if not API_URL:
        return {"status": "local", "message": "Running in Local Mode"}
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception:
        return {"status": "offline", "message": "API is waking up..."}

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
        st.image(thumbnail, width="stretch")
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

@st.cache_data(show_spinner=False)
def perform_semantic_search_cached(query, n_results=300, threshold=DISTANCE_THRESHOLD):
    if API_URL:
        try:
            # Increase timeout to 120s to handle cold starts and high load on Render Free tier
            response = requests.get(f"{API_URL}/semantic-search/", params={"q": query}, timeout=120)
            if response.status_code == 200:
                books_data = response.json()
                return [BookWrapper(b) for b in books_data]
            else:
                st.error(f"API Error: {response.status_code}. The server might still be initializing.")
                return []
        except Exception as e:
            st.error(f"API Connection Issue: {e}. Please wait a moment and try again.")
            return []

    if not HAS_LOCAL_DEPS:
        st.error("Local dependencies not found and API_URL not set.")
        return []

    manager = get_embedding_manager()
    session = get_db()
    
    results = manager.search(query, n_results=n_results)
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    if not ids:
        session.close()
        return []
        
    # Filter by threshold
    filtered_ids = [idx for idx, dist in zip(ids, distances) if dist <= threshold]
    
    if not filtered_ids:
        session.close()
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
    
    # Detach from session to allow serializing for cache
    session.expunge_all()
    session.close()
    return books

@st.cache_data(show_spinner=False)
def perform_keyword_search_cached(query):
    if API_URL:
        try:
            # Increase timeout to 30s to handle initial API connection
            response = requests.get(f"{API_URL}/search/", params={"q": query}, timeout=30)
            if response.status_code == 200:
                books_data = response.json()
                results = [BookWrapper(b) for b in books_data]
                return results, len(results)
            else:
                st.error(f"API Error: {response.status_code}")
                return [], 0
        except Exception as e:
            st.error(f"Failed to connect to API: {e}")
            return [], 0

    if not HAS_LOCAL_DEPS:
        st.error("Local dependencies not found and API_URL not set.")
        return [], 0

    session = get_db()
    search_term = f"%{query}%"
    query_obj = session.query(db.Book).filter(
        or_(
            db.Book.title.ilike(search_term),
            db.Book.authors.ilike(search_term),
            db.Book.isbn_13 == query
        )
    )
    results = query_obj.all()
    total = len(results)
    
    # Detach from session
    session.expunge_all()
    session.close()
    return results, total

def perform_semantic_search(query, manager, session, n_results=300, threshold=DISTANCE_THRESHOLD):
    # Keep original for internal calls if needed, but UI uses cached version
    return perform_semantic_search_cached(query, n_results, threshold)

def perform_keyword_search(query, session):
    return perform_keyword_search_cached(query)

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
    st.image("https://www.daiict.ac.in/sites/default/files/inline-images/Dhirubhai-Ambani-University-new-logo.jpg", width=250)
    
    st.divider()
    st.markdown("### Appearance")
    theme_choice = st.selectbox(
        "Theme",
        options=list(themes.keys()),
        index=list(themes.keys()).index(st.session_state.theme_choice)
    )
    if theme_choice != st.session_state.theme_choice:
        st.session_state.theme_choice = theme_choice
        st.rerun()

    st.divider()
    st.markdown("### Search Settings")
    search_mode = st.radio(
        "Search Mode",
        ["Semantic Search 🧠", "Keyword Search 🔍"],
        help="Semantic search finds meaning; Keyword search looks for exact text matches."
    )
    
    if "Semantic" in search_mode:
        st.info("💡 Semantic search is best for themes, topics, and descriptions.")
    else:
        st.info("💡 Keyword search is best for specific titles, authors, or ISBNs.")

    st.divider()
    st.markdown("### System Status")
    health = get_api_health()
    if health["status"] == "healthy":
        st.success("✅ API is Online & Ready")
    elif health["status"] == "loading":
        st.warning("⏳ API is Warming Up...")
    elif health["status"] == "offline":
        st.error("❌ API is Offline")
    else:
        st.info(f"ℹ️ {health['message']}")

# Main Search Area
query_input = st.text_input(
    "What are you looking for?", 
    placeholder="Search for a book, theme, or topic...",
    help="Type your query and press Enter. Click history chips below to reuse previous searches."
)

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown(f"**Version:** `{APP_VERSION}`")
    st.image("https://raw.githubusercontent.com/Falak-Parmar/Book-Finder/main/data/logo.png", width=250)
    hist_cols = st.columns(min(len(st.session_state.history), 5))
    for i, h_query in enumerate(reversed(st.session_state.history[-5:])):
        if hist_cols[i].button(h_query, key=f"hist_chip_{i}", width="stretch"):
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
    
    # Only perform search if it's a new query OR page reset
    # (Actually, in Streamlit, it usually re-renders. We can optimize but let's keep it simple first)
    with st.spinner("Finding the best matches..."):
        # For Semantic Search, we fetch a large pool and paginate locally
        # For Keyword Search, we fetch all and paginate locally (given the DB is small enough)
        # In a real app, we'd use offset/limit on the DB.
        if "active_query_results" not in st.session_state or st.session_state.last_final_query != final_query or st.session_state.get('last_search_mode') != search_mode:
            if "Semantic" in search_mode:
                results = perform_semantic_search_cached(final_query)
                total = len(results)
            else:
                results, total = perform_keyword_search_cached(final_query)
            
            st.session_state.active_query_results = results
            st.session_state.total_results = total
            st.session_state.last_search_mode = search_mode
    
    results = st.session_state.active_query_results
    total = st.session_state.total_results
    
    if not results:
        st.warning("No books found matching your query.")
    else:
        # Paging math
        start_idx = (st.session_state.page - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total)
        page_results = results[start_idx:end_idx]
        
        st.markdown(f'<div class="search-info">Showing {start_idx + 1} to {end_idx} of {total} results for \'{final_query}\'</div>', unsafe_allow_html=True)
        
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
                if st.button("Details", key=f"details_{book.isbn_13}_{i}", width="stretch"):
                    show_book_details(book)
        
        # Pagination Controls
        st.divider()
        col_prev, col_mid, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.session_state.page > 1:
                if st.button("← Previous Page", width="stretch"):
                    st.session_state.page -= 1
                    st.rerun()
        with col_mid:
            num_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
            st.markdown(f"<p style='text-align: center;'>Page <b>{st.session_state.page}</b> of {num_pages}</p>", unsafe_allow_html=True)
        with col_next:
            if end_idx < total:
                if st.button("Next Page →", width="stretch"):
                    st.session_state.page += 1
                    st.rerun()
else:
    st.write("---")
    st.markdown("""
    ### Popular Searches
    - *Modern machine learning techniques*
    - *Classic English literature*
    - *Books about the history of India*
    - *Introduction to quantum physics*
    """)
