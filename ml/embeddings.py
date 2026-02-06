from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
import os

# --- Configuration ---
MODEL_NAME = "all-MiniLM-L6-v2"
# Auto-detect vector store location
if os.path.exists("./data/vector_store"):
    DB_PATH = "data/vector_store"
elif os.path.exists("./vector_store"):
    DB_PATH = "vector_store"
else:
    DB_PATH = "data/vector_store"

COLLECTION_NAME = "books"

class EmbeddingManager:
    def __init__(self):
        # Ensure the parent directory exists for the path
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Initialize chroma client
        self.client = chromadb.PersistentClient(path=DB_PATH)
        
        # Initialize the embedding function
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=MODEL_NAME
        )
        
        # Link the internal model to avoid loading it twice in RAM (Saves ~200MB)
        self.model = self.embedding_fn._model
        
        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def generate_embeddings(self, texts):
        """
        Generates embeddings for a list of strings.
        """
        return self.model.encode(texts).tolist()

    def add_to_index(self, ids, texts, metadatas=None):
        """
        Adds documents to the vector index.
        """
        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )

    def search(self, query_text, n_results=10):
        """
        Searches the index for the most similar documents.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

if __name__ == "__main__":
    # Quick test
    manager = EmbeddingManager()
    print(f"ChromaDB collection '{COLLECTION_NAME}' initialized at {DB_PATH}")
