import pandas as pd
import json
import os

def generate_notebook():
    notebook_content = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Book-Finder Data Analysis\n",
                    "This notebook analyzes the ingestion and transformation metrics for the Book-Finder project."
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "import matplotlib.pyplot as plt\n",
                    "\n",
                    "# Paths\n",
                    "raw_path = '../data/raw/books_enriched.jsonl'\n",
                    "cleaned_path = '../data/processed/books_cleaned.jsonl'\n",
                    "\n",
                    "# Load Data\n",
                    "try:\n",
                    "    df_raw = pd.read_json(raw_path, lines=True)\n",
                    "    df_cleaned = pd.read_json(cleaned_path, lines=True)\n",
                    "    print(f\"Raw Data Loaded: {len(df_raw)} records\")\n",
                    "    print(f\"Cleaned Data Loaded: {len(df_cleaned)} records\")\n",
                    "except ValueError as e:\n",
                    "    print(f\"Error loading data: {e}\")"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Ingestion Metrics\n",
                    "if 'found' in df_raw.columns:\n",
                    "    total_processed = len(df_raw)\n",
                    "    successful_enrichment = df_raw['found'].sum()\n",
                    "    success_rate = (successful_enrichment / total_processed) * 100\n",
                    "    \n",
                    "    print(f\"Total Processed: {total_processed}\")\n",
                    "    print(f\"Successfully Enriched: {successful_enrichment}\")\n",
                    "    print(f\"Success Rate: {success_rate:.2f}%\")"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Cleaned Data Metrics\n",
                    "print(f\"Final Dataset Size: {len(df_cleaned)}\")\n",
                    "if 'isbn_13' in df_cleaned.columns:\n",
                    "    unique_isbns = df_cleaned['isbn_13'].nunique()\n",
                    "    print(f\"Unique ISBN-13s: {unique_isbns}\")"
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.8.5"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    with open('analysis/project_metrics.ipynb', 'w') as f:
        json.dump(notebook_content, f, indent=2)
    print("Notebook 'analysis/project_metrics.ipynb' created successfully.")

def analyze_metrics():
    print("Running Analysis...")
    try:
        # Paths relative to execution root
        raw_path = 'data/raw/books_enriched.jsonl'
        cleaned_path = 'data/processed/books_cleaned.jsonl'
        
        if not os.path.exists(raw_path) or not os.path.exists(cleaned_path):
             print(f"Data files not found. Checked {raw_path} and {cleaned_path}")
             return

        df_raw = pd.read_json(raw_path, lines=True)
        df_cleaned = pd.read_json(cleaned_path, lines=True)

        total_processed = len(df_raw)
        successful_enrichment = df_raw['found'].sum() if 'found' in df_raw.columns else 0
        success_rate = (successful_enrichment / total_processed) * 100 if total_processed > 0 else 0
        final_count = len(df_cleaned)
        
        print("\n=== Project Metrics ===")
        print(f"Total Books Processed: {total_processed}")
        print(f"Successfully Enriched (Google Books): {successful_enrichment}")
        print(f"Enrichment Success Rate: {success_rate:.1f}%")
        print(f"Final Deduplicated Dataset Size: {final_count}")
        print("=======================\n")
        
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    analyze_metrics()
    generate_notebook()
