from sentence_transformers import SentenceTransformer
import os

MODEL_NAME = "all-MiniLM-L6-v2"

def download():
    print(f"Downloading model: {MODEL_NAME}...")
    # This will download the model to the default cache directory (~/.cache/torch/sentence_transformers)
    # We can also specify a local path if we want to bundle it specifically.
    model = SentenceTransformer(MODEL_NAME)
    print("Model downloaded successfully.")

if __name__ == "__main__":
    download()
