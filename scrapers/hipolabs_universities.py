"""
Hipolabs Universities API scraper
Fetches German universities from the free Hipolabs API and stores in MongoDB
"""
import requests
import logging
from datetime import datetime
from models.mongo import get_db
from bson import ObjectId

logger = logging.getLogger(__name__)

HIPOLABS_API_URL = "http://universities.hipolabs.com/search"

def sync_german_universities():
    """
    Sync German universities from Hipolabs API to MongoDB
    Returns dict with sync statistics
    """
    try:
        logger.info("Starting German universities sync from Hipolabs API")
        db = get_db()
        
        # Fetch from API
        params = {'country': 'Germany'}
        response = requests.get(HIPOLABS_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        universities_data = response.json()
        logger.info(f"Fetched {len(universities_data)} universities from API")
        
        # Process and upsert
        synced = 0
        updated = 0
        errors = 0
        
        for uni_data in universities_data:
            try:
                # Normalize data
                university = {
                    'name': uni_data.get('name', '').strip(),
                    'alpha_two_code': uni_data.get('alpha_two_code', 'DE'),
                    'domains': uni_data.get('domains', []),
                    'web_pages': uni_data.get('web_pages', []),
                    'country': uni_data.get('country', 'Germany'),
                    'state-province': uni_data.get('state-province', '').strip() or None,
                    'last_synced_at': datetime.utcnow(),
                }
                
                if not university['name']:
                    continue
                
                # Check if exists (by name and state)
                query = {'name': university['name']}
                if university.get('state-province'):
                    query['state-province'] = university['state-province']
                
                existing = db.universities.find_one(query)
                
                if existing:
                    # Update existing
                    db.universities.update_one(
                        {'_id': existing['_id']},
                        {'$set': university}
                    )
                    updated += 1
                else:
                    # Insert new
                    university['created_at'] = datetime.utcnow()
                    db.universities.insert_one(university)
                    synced += 1
                    
            except Exception as e:
                logger.error(f"Error processing university {uni_data.get('name')}: {e}")
                errors += 1
                continue
        
        result = {
            'total_fetched': len(universities_data),
            'synced': synced,
            'updated': updated,
            'errors': errors,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"University sync completed: {result}")
        
        # Log job
        db.jobs_log.insert_one({
            'job_type': 'sync_universities',
            'status': 'success' if errors == 0 else 'partial',
            'result': result,
            'created_at': datetime.utcnow()
        })
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Network error during university sync: {e}")
        db = get_db()
        db.jobs_log.insert_one({
            'job_type': 'sync_universities',
            'status': 'error',
            'error': str(e),
            'created_at': datetime.utcnow()
        })
        raise
    except Exception as e:
        logger.error(f"Unexpected error during university sync: {e}")
        db = get_db()
        db.jobs_log.insert_one({
            'job_type': 'sync_universities',
            'status': 'error',
            'error': str(e),
            'created_at': datetime.utcnow()
        })
        raise

