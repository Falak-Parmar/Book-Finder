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
    logger.info("Starting Pipeline Orchestration...")
    
    # 1. Sync Step
    sync_cmd = f"{sys.executable} sync_pipeline.py"
    logger.info("Step 1: Synchronizing with OPAC...")
    
    # Run sync manually to check exit code
    import subprocess as sp
    sync_process = sp.run(sync_cmd, shell=True, cwd=os.getcwd())
    sync_code = sync_process.returncode
    
    ingestion_input = "data/raw/Accession Register-Books.csv"
    skip_rest = False
    
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

    steps = [
        (f"{sys.executable} ingestion/ingestion.py --input '{ingestion_input}' --limit 50", "Google Books Ingestion"),
        (f"{sys.executable} transformation/transformation.py", "Data Transformation"),
        (f"{sys.executable} storage/storage.py", "Database Storage")
    ]
    
    for cmd, name in steps:
        if not run_step(cmd, name):
            logger.error(f"{name} failed. Pipeline stopped.")
            sys.exit(1)
            
    logger.info("Pipeline executed successfully.")

if __name__ == "__main__":
    main()
