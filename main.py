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
            stderr=subprocess.PIPE,
            text=True
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
    steps = [
        (f"{sys.executable} sync_pipeline.py", "Sync & Download"),
        (f"{sys.executable} ingestion/ingestion.py", "Google Books Ingestion"),
        (f"{sys.executable} transformation/transformation.py", "Data Transformation"),
        (f"{sys.executable} storage/storage.py", "Database Storage")
    ]
    
    for cmd, name in steps:
        if not run_step(cmd, name):
            logger.error("Pipeline stopped due to error.")
            sys.exit(1)
            
    logger.info("Pipeline executed successfully.")

if __name__ == "__main__":
    main()
