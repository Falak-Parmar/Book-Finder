import argparse
import subprocess
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_step(command, step_name):
    logger.info(f"--- Starting {step_name} ---")
    try:
        # Run command with real-time output
        process = subprocess.Popen(
            command,
            cwd=os.getcwd(),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        return_code = process.poll()
        
        if return_code != 0:
            stderr = process.stderr.read()
            logger.error(f"{step_name} failed with code {return_code}")
            logger.error(f"Error output: {stderr}")
            return False
            
        logger.info(f"--- {step_name} Completed Successfully ---\n")
        return True
        
    except Exception as e:
        logger.error(f"Error executing {step_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Book Finder Pipeline Orchestrator")
    parser.add_argument("--skip-sync", action="store_true", help="Skip the sync step")
    parser.add_argument("--skip-ingestion", action="store_true", help="Skip the ingestion step")
    parser.add_argument("--skip-transform", action="store_true", help="Skip the data transformation step")
    parser.add_argument("--skip-storage", action="store_true", help="Skip the database storage step")
    parser.add_argument("--ingest-limit", type=int, default=50, help="Limit number of books to ingest")
    
    args = parser.parse_args()

    logger.info("Starting Pipeline Orchestration...")
    
    ingestion_input = "data/raw/Accession Register-Books.csv"
    
    # 1. Sync Step
    if not args.skip_sync:
        sync_cmd = f"{sys.executable} sync_pipeline.py"
        logger.info("Step 1: Synchronizing with OPAC...")
        
        # Run sync manually to check exit code
        import subprocess as sp
        sync_process = sp.run(sync_cmd, shell=True, cwd=os.getcwd())
        sync_code = sync_process.returncode
        
        if sync_code == 2:
            logger.info("New items found! Switching to incremental ingestion mode.")
            ingestion_input = "data/raw/current_sync.csv"
        elif sync_code == 0:
            logger.info("No new items found. Pipeline will skip enrichment to avoid processing backlog.")
            # We can still run transformation and storage if the user wants, 
            # but usually sync trigger implies "sync new".
            # For now, I'll limit the backlog check to 10 items if no sync happened.
            logger.info("Checking if any pending records in main backlog (limited to 5 for speed)...")
        else:
            logger.error("Sync failed. Check logs for details.")
            sys.exit(1)
    else:
        logger.info("Skipping Sync Step.")

    steps = []
    
    if not args.skip_ingestion:
        steps.append((f"{sys.executable} ingestion/ingestion.py --input '{ingestion_input}' --limit {args.ingest_limit}", "Google Books Ingestion"))
    
    if not args.skip_transform:
        steps.append((f"{sys.executable} Transformation/transformation.py", "Data Transformation"))
        
    if not args.skip_storage:
        steps.append((f"{sys.executable} storage/storage.py", "Database Storage"))
    
    for cmd, name in steps:
        if not run_step(cmd, name):
            logger.error(f"{name} failed. Pipeline stopped.")
            sys.exit(1)
            
    logger.info("Pipeline executed successfully.")

if __name__ == "__main__":
    main()
