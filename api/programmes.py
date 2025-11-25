"""
Programmes API endpoints
Handles programme search, detail views, and admin scraper triggers
"""
from flask import Blueprint, request, jsonify
from models.mongo import get_db
from utils.auth import get_user_id, require_admin
from scrapers.daad_programmes import scrape_german_programmes
from bson import ObjectId
import logging

bp = Blueprint('programmes', __name__)
logger = logging.getLogger(__name__)

@bp.route('/programmes', methods=['GET'])
def list_programmes():
    """
    GET /api/programmes
    List programmes with search and filter options
    
    Query parameters:
    - q: search query (title)
    - degree_type: filter by degree type (Bachelor, Master, PhD, etc.)
    - language: filter by language of instruction
    - university_id: filter by university ID
    - city: filter by city
    - page: page number (default: 1)
    - limit: results per page (default: 20, max: 100)
    """
    try:
        db = get_db()
        
        # Get query parameters
        search_query = request.args.get('q', '').strip()
        degree_type = request.args.get('degree_type', '').strip()
        language = request.args.get('language', '').strip()
        university_id = request.args.get('university_id', '').strip()
        city = request.args.get('city', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, max(1, int(request.args.get('limit', 20))))
        
        # Build query
        query = {}
        
        if search_query:
            query['$text'] = {'$search': search_query}
        
        if degree_type:
            query['degree_type'] = {'$regex': degree_type, '$options': 'i'}
        
        if language:
            query['language'] = {'$in': [language]}
        
        if university_id:
            if ObjectId.is_valid(university_id):
                query['university_id'] = university_id
            else:
                query['university_name'] = {'$regex': university_id, '$options': 'i'}
        
        if city:
            query['city'] = {'$regex': city, '$options': 'i'}
        
        # Get total count
        total = db.programmes.count_documents(query)
        
        # Pagination
        skip = (page - 1) * limit
        
        # Execute query
        cursor = db.programmes.find(query).skip(skip).limit(limit).sort('title', 1)
        programmes = list(cursor)
        
        # Convert ObjectId to string and ensure all fields exist
        for prog in programmes:
            prog['_id'] = str(prog['_id'])
            prog.setdefault('title', 'Unknown')
            prog.setdefault('degree_type', '')
            prog.setdefault('language', [])
            prog.setdefault('university_name', '')
            prog.setdefault('city', '')
            prog.setdefault('tuition_fee_eur_per_semester', None)
            prog.setdefault('duration_semesters', None)
            prog.setdefault('source', '')
            prog.setdefault('source_url', '')
        
        return jsonify({
            'programmes': programmes,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing programmes: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/programmes/<programme_id>', methods=['GET'])
def get_programme(programme_id):
    """
    GET /api/programmes/<id>
    Get detailed information about a specific programme
    """
    try:
        if not ObjectId.is_valid(programme_id):
            return jsonify({'error': 'Invalid programme ID', 'code': 'INVALID_ID'}), 400
        
        db = get_db()
        programme = db.programmes.find_one({'_id': ObjectId(programme_id)})
        
        if not programme:
            return jsonify({'error': 'Programme not found', 'code': 'NOT_FOUND'}), 404
        
        # Convert ObjectId to string
        programme['_id'] = str(programme['_id'])
        
        # Get university info if university_id exists
        if programme.get('university_id'):
            university = db.universities.find_one({'_id': ObjectId(programme['university_id'])})
            if university:
                university['_id'] = str(university['_id'])
                programme['university'] = university
        
        return jsonify(programme), 200
        
    except Exception as e:
        logger.error(f"Error getting programme: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/programmes/filters', methods=['GET'])
def get_filters():
    """
    GET /api/programmes/filters
    Get available filter values (degree types, languages, cities)
    """
    try:
        db = get_db()
        
        degree_types = db.programmes.distinct('degree_type')
        languages = db.programmes.distinct('language')
        cities = db.programmes.distinct('city')
        
        # Flatten language array
        all_languages = set()
        for lang_list in languages:
            if isinstance(lang_list, list):
                all_languages.update(lang_list)
            else:
                all_languages.add(lang_list)
        
        return jsonify({
            'degree_types': sorted([d for d in degree_types if d]),
            'languages': sorted([l for l in all_languages if l]),
            'cities': sorted([c for c in cities if c])
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting filters: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/admin/programmes/scrape', methods=['POST'])
@require_admin
def trigger_scrape():
    """
    POST /api/admin/programmes/scrape
    Trigger manual scraping of German programmes
    Admin only
    """
    try:
        result = scrape_german_programmes()
        return jsonify({
            'message': 'Programme scraping completed',
            'result': result
        }), 200
    except Exception as e:
        logger.error(f"Error scraping programmes: {e}")
        return jsonify({'error': str(e), 'code': 'SCRAPE_ERROR'}), 500

