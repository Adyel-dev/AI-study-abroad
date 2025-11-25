"""
Intelligent database querying for counselor
Extracts search parameters from user messages and queries programmes/universities
"""
import logging
from models.mongo import get_db
from services.embeddings import search_similar
from config import Config
import re
import json

logger = logging.getLogger(__name__)

def extract_search_intent(user_message: str, conversation_history: list = None):
    """
    Extract search parameters from user message using AI (OpenRouter/OpenAI)
    Returns dict with: field, degree_type, language, city, etc.
    """
    try:
        from services.ai_client import chat_completion
        
        history_context = ""
        if conversation_history:
            recent = conversation_history[-3:]  # Last 3 messages
            history_context = "\nRecent conversation:\n"
            for msg in recent:
                history_context += f"{msg.get('sender', 'user')}: {msg.get('message_text', '')}\n"
        
        prompt = f"""Extract search parameters for finding study programmes from this message. Return ONLY a JSON object with these fields:
- field: field of study (e.g., "IT", "Computer Science", "Business", "Engineering")
- degree_type: "Bachelor", "Master", "PhD", or null
- language: "English", "German", or null
- city: city name if mentioned, or null
- keywords: array of important keywords from the message

Message: {user_message}
{history_context}

Return JSON only, no explanation:"""

        ai_response = chat_completion(
            messages=[
                {"role": "system", "content": "You are a helper that extracts structured data from messages. Always return valid JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        content = ai_response['content'].strip()
        # Remove markdown code blocks if present
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()
        
        intent = json.loads(content)
        return intent
        
    except Exception as e:
        logger.error(f"Error extracting search intent: {e}")
        # Fallback: simple keyword extraction
        return {
            'field': None,
            'degree_type': None,
            'language': None,
            'city': None,
            'keywords': []
        }

def query_programmes_intelligent(search_params: dict, user_profile: dict = None, limit: int = 10):
    """
    Query programmes database using extracted search parameters
    """
    try:
        db = get_db()
        query = {}
        
        # Build query from search parameters
        if search_params.get('degree_type'):
            degree = search_params['degree_type']
            if isinstance(degree, str):
                query['degree_type'] = {'$regex': degree, '$options': 'i'}
        
        if search_params.get('field'):
            field = search_params['field']
            query['title'] = {'$regex': field, '$options': 'i'}
        
        if search_params.get('language'):
            lang = search_params['language']
            # Language field is an array, so use $in to match any element
            query['language'] = {'$in': [lang, lang.lower(), lang.upper(), lang.capitalize()]}
        
        if search_params.get('city'):
            city = search_params['city']
            query['city'] = {'$regex': city, '$options': 'i'}
        
        # Also use profile preferences if available
        if user_profile:
            if not query.get('degree_type') and user_profile.get('desired_study_level'):
                level = user_profile['desired_study_level']
                if 'Master' in level:
                    query['degree_type'] = {'$regex': 'Master', '$options': 'i'}
                elif 'Bachelor' in level:
                    query['degree_type'] = {'$regex': 'Bachelor', '$options': 'i'}
            
            if not query.get('title') and user_profile.get('desired_field'):
                field = user_profile['desired_field']
                query['title'] = {'$regex': field, '$options': 'i'}
            
            if user_profile.get('preferred_cities') and not query.get('city'):
                cities = user_profile['preferred_cities']
                query['city'] = {'$in': cities}
        
        # Execute query
        programmes = list(db.programmes.find(query).limit(limit))
        
        # Convert ObjectIds
        for prog in programmes:
            prog['_id'] = str(prog['_id'])
        
        return programmes
        
    except Exception as e:
        logger.error(f"Error querying programmes: {e}")
        return []

def query_universities_intelligent(search_params: dict, user_profile: dict = None, limit: int = 10):
    """
    Query universities database using search parameters
    """
    try:
        db = get_db()
        query = {'country': 'Germany'}
        
        if search_params.get('city'):
            city = search_params['city']
            query['state-province'] = {'$regex': city, '$options': 'i'}
        
        # Also search by name if field matches university specialties
        if search_params.get('keywords'):
            keywords = ' '.join(search_params['keywords'])
            query['$text'] = {'$search': keywords}
        
        universities = list(db.universities.find(query).limit(limit))
        
        for uni in universities:
            uni['_id'] = str(uni['_id'])
        
        return universities
        
    except Exception as e:
        logger.error(f"Error querying universities: {e}")
        return []
