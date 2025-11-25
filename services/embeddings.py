"""
Embeddings service for RAG (Retrieval Augmented Generation)
Handles text embedding generation and similarity search
"""
import openai
import numpy as np
import logging
from typing import List, Dict, Any
from datetime import datetime
from models.mongo import get_db
from config import Config
from bson import ObjectId
import httpx

logger = logging.getLogger(__name__)

# Initialize OpenAI client
_openai_client = None

def get_openai_client():
    """Get OpenAI client instance"""
    global _openai_client
    if _openai_client is None:
        # Create httpx client without proxies to avoid compatibility issues
        http_client = httpx.Client(timeout=60.0)
        _openai_client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            http_client=http_client
        )
    return _openai_client

def embed_text(text: str) -> List[float]:
    """
    Generate embedding for a text using OpenAI API
    
    Args:
        text: Text to embed
    
    Returns:
        List of floats representing the embedding vector
    """
    try:
        if not text or not text.strip():
            return None
        
        client = get_openai_client()
        response = client.embeddings.create(
            model=Config.OPENAI_EMBEDDING_MODEL,
            input=text.strip()
        )
        
        return response.data[0].embedding
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    try:
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)
        
        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0

def search_similar(query: str, collection_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for similar documents using embedding similarity
    
    Args:
        query: Search query text
        collection_name: Name of the collection to search (universities, programmes, immigration_rules)
        limit: Maximum number of results to return
    
    Returns:
        List of similar documents with similarity scores
    """
    try:
        # Generate query embedding
        query_embedding = embed_text(query)
        if not query_embedding:
            return []
        
        db = get_db()
        
        # Get all embeddings for the collection
        embeddings = list(db.embeddings.find({
            'collection_name': collection_name
        }))
        
        if not embeddings:
            logger.warning(f"No embeddings found for collection: {collection_name}")
            return []
        
        # Calculate similarities
        results = []
        for emb_doc in embeddings:
            stored_embedding = emb_doc.get('embedding')
            if not stored_embedding:
                continue
            
            similarity = cosine_similarity(query_embedding, stored_embedding)
            
            results.append({
                'document_id': emb_doc.get('document_id'),
                'similarity': similarity,
                'metadata': emb_doc.get('metadata', {})
            })
        
        # Sort by similarity (descending) and limit
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:limit]
        
        # Fetch actual documents
        similar_docs = []
        collection = db[collection_name]
        
        for result in results:
            doc_id = result['document_id']
            try:
                if ObjectId.is_valid(doc_id):
                    doc = collection.find_one({'_id': ObjectId(doc_id)})
                else:
                    doc = collection.find_one({'_id': doc_id})
                
                if doc:
                    doc['_id'] = str(doc['_id'])
                    doc['similarity_score'] = result['similarity']
                    similar_docs.append(doc)
            except Exception as e:
                logger.warning(f"Could not fetch document {doc_id}: {e}")
                continue
        
        return similar_docs
        
    except Exception as e:
        logger.error(f"Error searching similar documents: {e}")
        return []

def index_document(collection_name: str, document_id: str, text: str, metadata: Dict = None):
    """
    Create and store embedding for a document
    
    Args:
        collection_name: Name of the collection (universities, programmes, immigration_rules)
        document_id: ID of the document
        text: Text content to embed
        metadata: Additional metadata to store
    """
    try:
        embedding = embed_text(text)
        if not embedding:
            logger.warning(f"Could not generate embedding for document {document_id}")
            return False
        
        db = get_db()
        
        # Check if embedding already exists
        existing = db.embeddings.find_one({
            'collection_name': collection_name,
            'document_id': document_id
        })
        
        embedding_doc = {
            'collection_name': collection_name,
            'document_id': document_id,
            'embedding': embedding,
            'metadata': metadata or {},
            'updated_at': datetime.utcnow()
        }
        
        if existing:
            # Update existing
            db.embeddings.update_one(
                {'_id': existing['_id']},
                {'$set': embedding_doc}
            )
        else:
            # Insert new
            embedding_doc['created_at'] = datetime.utcnow()
            db.embeddings.insert_one(embedding_doc)
        
        return True
        
    except Exception as e:
        logger.error(f"Error indexing document: {e}")
        return False

def index_collection(collection_name: str):
    """
    Index all documents in a collection (generate embeddings)
    Useful for initial setup or re-indexing
    
    Args:
        collection_name: Name of the collection to index
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Build text content based on collection type
        documents = list(collection.find({}))
        
        indexed = 0
        failed = 0
        
        for doc in documents:
            doc_id = str(doc['_id'])
            
            # Extract text content based on collection type
            if collection_name == 'universities':
                text_parts = [
                    doc.get('name', ''),
                    doc.get('state-province', ''),
                    ' '.join(doc.get('domains', []))
                ]
                text = ' '.join([p for p in text_parts if p])
                metadata = {
                    'name': doc.get('name'),
                    'state': doc.get('state-province')
                }
            elif collection_name == 'programmes':
                text_parts = [
                    doc.get('title', ''),
                    doc.get('degree_type', ''),
                    doc.get('university_name', ''),
                    doc.get('city', ''),
                    ' '.join(doc.get('language', []))
                ]
                text = ' '.join([p for p in text_parts if p])
                metadata = {
                    'title': doc.get('title'),
                    'degree_type': doc.get('degree_type'),
                    'university_name': doc.get('university_name')
                }
            elif collection_name == 'immigration_rules':
                text_parts = [
                    doc.get('visa_type', ''),
                    str(doc.get('min_funds_year_eur', '')),
                    str(doc.get('work_hours_per_week', '')),
                    ' '.join(doc.get('key_documents', []))
                ]
                text = ' '.join([p for p in text_parts if p])
                metadata = {
                    'visa_type': doc.get('visa_type'),
                    'country_code': doc.get('country_code')
                }
            else:
                logger.warning(f"Unknown collection type: {collection_name}")
                continue
            
            if text:
                success = index_document(collection_name, doc_id, text, metadata)
                if success:
                    indexed += 1
                else:
                    failed += 1
        
        logger.info(f"Indexed {indexed} documents from {collection_name}, {failed} failed")
        return {'indexed': indexed, 'failed': failed}
        
    except Exception as e:
        logger.error(f"Error indexing collection {collection_name}: {e}")
        raise


