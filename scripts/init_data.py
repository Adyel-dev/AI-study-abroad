"""
Initialize database with initial data if empty
Run on startup to ensure database has basic data
"""
import logging
from models.mongo import get_db
from scrapers.hipolabs_universities import sync_german_universities
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

def initialize_database_if_empty():
    """
    Initialize database with initial data if collections are empty
    Returns True if initialization was performed, False if data already exists
    """
    try:
        db = get_db()
        
        # Check if databases need initialization
        needs_init = False
        init_actions = []
        
        # Check universities
        university_count = db.universities.count_documents({})
        if university_count == 0:
            logger.info("Universities collection is empty - will sync on startup")
            needs_init = True
            init_actions.append('sync_universities')
        
        # Check immigration rules
        immigration_count = db.immigration_rules.count_documents({})
        if immigration_count == 0:
            logger.info("Immigration rules collection is empty - will seed on startup")
            needs_init = True
            init_actions.append('seed_immigration')
        
        if not needs_init:
            logger.info("Database already has data - skipping initialization")
            return False
        
        logger.info(f"Initializing database with: {', '.join(init_actions)}")
        
        # Run initialization actions
        if 'sync_universities' in init_actions:
            try:
                logger.info("Syncing universities from Hipolabs API...")
                result = sync_german_universities()
                logger.info(f"Universities sync completed: {result}")
            except Exception as e:
                logger.error(f"Error syncing universities: {e}")
        
        if 'seed_immigration' in init_actions:
            try:
                logger.info("Seeding immigration rules...")
                # Import seed function - ensure path is correct
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from scripts.seed_immigration_rules import seed_immigration_rules
                seed_immigration_rules()
                logger.info("Immigration rules seeded successfully")
            except Exception as e:
                logger.error(f"Error seeding immigration rules: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info("Database initialization completed")
        return True
        
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    initialize_database_if_empty()

