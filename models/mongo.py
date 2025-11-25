"""
MongoDB connection and collection management
Provides database connection and ensures indexes are created
"""
from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.operations import IndexModel
from pymongo.errors import ConnectionFailure
import logging
from config import Config

logger = logging.getLogger(__name__)

# Global database instance
_db = None
_client = None

def get_db():
    """
    Get MongoDB database instance (singleton pattern)
    Creates connection if not already established
    """
    global _db, _client
    
    if _db is None:
        try:
            _client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            _client.admin.command('ping')
            _db = _client[Config.DB_NAME]
            logger.info(f"Connected to MongoDB: {Config.DB_NAME}")
            
            # Create indexes
            create_indexes(_db)
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    return _db

def create_indexes(db):
    """
    Create indexes for all collections to optimize query performance
    """
    try:
        # Universities collection indexes
        db.universities.create_indexes([
            IndexModel([('name', ASCENDING), ('state-province', ASCENDING)]),
            IndexModel([('state-province', ASCENDING)]),
            IndexModel([('country', ASCENDING)]),
            IndexModel([('name', TEXT)]),
        ])
        
        # Programmes collection indexes
        db.programmes.create_indexes([
            IndexModel([('degree_type', ASCENDING)]),
            IndexModel([('language', ASCENDING)]),
            IndexModel([('university_id', ASCENDING)]),
            IndexModel([('city', ASCENDING)]),
            IndexModel([('title', TEXT)]),
            IndexModel([('last_seen_at', ASCENDING)]),
        ])
        
        # Immigration rules collection indexes
        db.immigration_rules.create_indexes([
            IndexModel([('country_code', ASCENDING)]),
            IndexModel([('visa_type', ASCENDING)]),
            IndexModel([('country_code', ASCENDING), ('visa_type', ASCENDING)]),
        ])
        
        # Student profiles collection indexes
        db.student_profiles.create_indexes([
            IndexModel([('user_id', ASCENDING)]),
            IndexModel([('created_at', ASCENDING)]),
        ])
        
        # Documents collection indexes
        db.documents.create_indexes([
            IndexModel([('user_id', ASCENDING)]),
            IndexModel([('document_type', ASCENDING)]),
            IndexModel([('uploaded_at', ASCENDING)]),
        ])
        
        # Assessments collection indexes
        db.assessments.create_indexes([
            IndexModel([('user_id', ASCENDING)]),
            IndexModel([('created_at', ASCENDING)]),
            IndexModel([('user_id', ASCENDING), ('created_at', ASCENDING)]),
        ])
        
        # Counseling sessions collection indexes
        db.counseling_sessions.create_indexes([
            IndexModel([('user_id', ASCENDING)]),
            IndexModel([('created_at', ASCENDING)]),
            IndexModel([('user_id', ASCENDING), ('created_at', ASCENDING)]),
        ])
        
        # Counseling messages collection indexes
        db.counseling_messages.create_indexes([
            IndexModel([('session_id', ASCENDING)]),
            IndexModel([('created_at', ASCENDING)]),
            IndexModel([('session_id', ASCENDING), ('created_at', ASCENDING)]),
        ])
        
        # Counseling plans collection indexes
        db.counseling_plans.create_indexes([
            IndexModel([('user_id', ASCENDING)]),
            IndexModel([('session_id', ASCENDING)]),
            IndexModel([('last_updated_at', ASCENDING)]),
        ])
        
        # Shortlisted programmes collection indexes
        db.shortlisted_programmes.create_indexes([
            IndexModel([('user_id', ASCENDING)]),
            IndexModel([('programme_id', ASCENDING)]),
            IndexModel([('user_id', ASCENDING), ('programme_id', ASCENDING)], unique=True),
        ])
        
        # Jobs log collection indexes
        db.jobs_log.create_indexes([
            IndexModel([('job_type', ASCENDING)]),
            IndexModel([('created_at', ASCENDING)]),
            IndexModel([('status', ASCENDING)]),
        ])
        
        # Embeddings collection indexes (for RAG)
        db.embeddings.create_indexes([
            IndexModel([('collection_name', ASCENDING)]),
            IndexModel([('document_id', ASCENDING)]),
            IndexModel([('collection_name', ASCENDING), ('document_id', ASCENDING)]),
        ])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        # Don't raise - indexes may already exist

def close_connection():
    """Close MongoDB connection"""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")

