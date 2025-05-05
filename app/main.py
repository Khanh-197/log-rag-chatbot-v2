import os
import time
import threading
import logging
from dotenv import load_dotenv
from rag_pipeline import RAGPipeline

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Global RAG pipeline instance
rag_pipeline = None

def refresh_logs_periodically():
    """Refresh logs periodically based on the refresh interval."""
    global rag_pipeline
    
    refresh_interval = int(os.getenv("REFRESH_INTERVAL", "300"))  # Default: 5 minutes
    
    while True:
        logger.info("Starting periodic log refresh")
        try:
            logs_count = rag_pipeline.refresh_logs()
            logger.info(f"Refreshed {logs_count} logs")
        except Exception as e:
            logger.error(f"Error refreshing logs: {e}")
        
        # Sleep until next refresh
        logger.info(f"Next refresh in {refresh_interval} seconds")
        time.sleep(refresh_interval)

def init_application():
    """Initialize the application."""
    global rag_pipeline
    
    logger.info("Initializing RAG pipeline")
    rag_pipeline = RAGPipeline()
    
    # Initial log loading
    logger.info("Loading initial logs")
    try:
        logs_count = rag_pipeline.refresh_logs()
        logger.info(f"Loaded {logs_count} initial logs")
    except Exception as e:
        logger.error(f"Error loading initial logs: {e}")
    
    # Start background refresh thread
    refresh_thread = threading.Thread(target=refresh_logs_periodically, daemon=True)
    refresh_thread.start()
    
    logger.info("Application initialization complete")
    return rag_pipeline

# Get or initialize RAG pipeline
def get_rag_pipeline():
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = init_application()
    return rag_pipeline

if __name__ == "__main__":
    # This will be executed when running this file directly (not through Streamlit)
    init_application()
