"""
Universities API endpoints
Handles university search, detail views, and admin sync operations
"""
from flask import Blueprint, request, jsonify
from models.mongo import get_db
from utils.auth import get_user_id, require_admin
from scrapers.hipolabs_universities import sync_german_universities
from bson import ObjectId
import logging

bp = Blueprint('universities', __name__)
logger = logging.getLogger(__name__)

@bp.route('/universities', methods=['GET'])
def list_universities():
    """
    GET /api/universities
    List universities with search and filter options
    
    Query parameters:
    - q: search query (name)
    - state: filter by state/province
    - page: page number (default: 1)
    - limit: results per page (default: 20, max: 100)
    """
    try:
        db = get_db()
        
        # Get query parameters
        search_query = request.args.get('q', '').strip()
        state_filter = request.args.get('state', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, max(1, int(request.args.get('limit', 20))))
        
        # Build query
        query = {'country': 'Germany'}
        
        if state_filter:
            query['state-province'] = state_filter
        
        if search_query:
            query['$text'] = {'$search': search_query}
        
        # Get total count
        total = db.universities.count_documents(query)
        
        # Pagination
        skip = (page - 1) * limit
        
        # Execute query
        cursor = db.universities.find(query).skip(skip).limit(limit).sort('name', 1)
        universities = list(cursor)
        
        # Convert ObjectId to string
        for uni in universities:
            uni['_id'] = str(uni['_id'])
            # Ensure all expected fields exist
            uni.setdefault('name', 'Unknown')
            uni.setdefault('domains', [])
            uni.setdefault('web_pages', [])
            uni.setdefault('state-province', '')
            uni.setdefault('alpha_two_code', 'DE')
        
        return jsonify({
            'universities': universities,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing universities: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/universities/<university_id>', methods=['GET'])
def get_university(university_id):
    """
    GET /api/universities/<id>
    Get detailed information about a specific university
    """
    try:
        if not ObjectId.is_valid(university_id):
            return jsonify({'error': 'Invalid university ID', 'code': 'INVALID_ID'}), 400
        
        db = get_db()
        university = db.universities.find_one({'_id': ObjectId(university_id)})
        
        if not university:
            return jsonify({'error': 'University not found', 'code': 'NOT_FOUND'}), 404
        
        # Convert ObjectId to string
        university['_id'] = str(university['_id'])
        
        # Get related programmes
        programmes = list(db.programmes.find(
            {'university_id': university_id}
        ).limit(10))
        
        for prog in programmes:
            prog['_id'] = str(prog['_id'])
        
        university['related_programmes'] = programmes
        
        return jsonify(university), 200
        
    except Exception as e:
        logger.error(f"Error getting university: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/admin/universities/sync', methods=['POST'])
@require_admin
def sync_universities():
    """
    POST /api/admin/universities/sync
    Trigger manual sync of German universities from Hipolabs API
    Admin only
    """
    try:
        result = sync_german_universities()
        return jsonify({
            'message': 'University sync completed',
            'result': result
        }), 200
    except Exception as e:
        logger.error(f"Error syncing universities: {e}")
        return jsonify({'error': str(e), 'code': 'SYNC_ERROR'}), 500

@bp.route('/universities/states', methods=['GET'])
def list_states():
    """
    GET /api/universities/states
    Get list of all German states that have universities
    """
    try:
        db = get_db()
        states = db.universities.distinct('state-province')
        states = [s for s in states if s]  # Filter out None/empty
        states.sort()
        return jsonify({'states': states}), 200
    except Exception as e:
        logger.error(f"Error getting states: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

