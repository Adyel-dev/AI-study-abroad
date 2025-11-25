"""
Admin API endpoints
Handles admin authentication, job triggers, and immigration rules management
"""
from flask import Blueprint, request, jsonify, session
from models.mongo import get_db
from utils.auth import require_admin
from scrapers.hipolabs_universities import sync_german_universities
from scrapers.daad_programmes import scrape_german_programmes
from services.embeddings import index_collection
from config import Config
from bson import ObjectId
from datetime import datetime
import logging

bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@bp.route('/login', methods=['POST'])
def admin_login():
    """
    POST /api/admin/login
    Admin login endpoint
    
    Request body:
    - username: admin username
    - password: admin password
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'code': 'INVALID_DATA'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return jsonify({
                'message': 'Login successful',
                'admin': True
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials', 'code': 'INVALID_CREDENTIALS'}), 401
            
    except Exception as e:
        logger.error(f"Error in admin login: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/logout', methods=['POST'])
def admin_logout():
    """POST /api/admin/logout - Admin logout"""
    session.pop('admin_logged_in', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@bp.route('/jobs', methods=['GET'])
@require_admin
def get_job_logs():
    """
    GET /api/admin/jobs
    Get job execution logs
    Query params: job_type, status, limit
    """
    try:
        db = get_db()
        
        job_type = request.args.get('job_type', '').strip()
        status = request.args.get('status', '').strip()
        limit = min(100, max(1, int(request.args.get('limit', 50))))
        
        query = {}
        if job_type:
            query['job_type'] = job_type
        if status:
            query['status'] = status
        
        logs = list(db.jobs_log.find(query).sort('created_at', -1).limit(limit))
        
        for log in logs:
            log['_id'] = str(log['_id'])
            if 'created_at' in log:
                log['created_at'] = log['created_at'].isoformat() if hasattr(log['created_at'], 'isoformat') else str(log['created_at'])
        
        return jsonify({'jobs': logs}), 200
        
    except Exception as e:
        logger.error(f"Error getting job logs: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/jobs/trigger', methods=['POST'])
@require_admin
def trigger_job():
    """
    POST /api/admin/jobs/trigger
    Trigger a specific job
    
    Request body:
    - job_type: 'sync_universities', 'scrape_programmes', 'index_embeddings', 'check_immigration'
    - collection: for index_embeddings, specify collection name
    """
    try:
        data = request.get_json()
        if not data or 'job_type' not in data:
            return jsonify({'error': 'job_type required', 'code': 'INVALID_DATA'}), 400
        
        job_type = data.get('job_type')
        result = None
        
        if job_type == 'sync_universities':
            result = sync_german_universities()
        elif job_type == 'scrape_programmes':
            result = scrape_german_programmes()
        elif job_type == 'index_embeddings':
            collection = data.get('collection', 'universities')
            result = index_collection(collection)
        elif job_type == 'check_immigration':
            # Placeholder for immigration check
            result = {'message': 'Immigration check not implemented yet'}
        else:
            return jsonify({'error': 'Invalid job_type', 'code': 'INVALID_JOB_TYPE'}), 400
        
        return jsonify({
            'message': f'Job {job_type} completed',
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error triggering job: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/immigration-rules', methods=['GET'])
@require_admin
def list_immigration_rules():
    """GET /api/admin/immigration-rules - List all immigration rules"""
    try:
        db = get_db()
        rules = list(db.immigration_rules.find({}).sort('country_code', 1))
        
        for rule in rules:
            rule['_id'] = str(rule['_id'])
        
        return jsonify({'rules': rules}), 200
        
    except Exception as e:
        logger.error(f"Error listing immigration rules: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/immigration-rules', methods=['POST'])
@require_admin
def create_immigration_rule():
    """POST /api/admin/immigration-rules - Create new immigration rule"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'code': 'INVALID_DATA'}), 400
        
        required_fields = ['country_code', 'visa_type']
        missing = [f for f in required_fields if f not in data or not data[f]]
        if missing:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing)}',
                'code': 'MISSING_FIELDS'
            }), 400
        
        db = get_db()
        
        rule_doc = {
            'country_code': data['country_code'].upper(),
            'visa_type': data['visa_type'],
            'min_funds_month_eur': data.get('min_funds_month_eur'),
            'min_funds_year_eur': data.get('min_funds_year_eur'),
            'work_hours_per_week': data.get('work_hours_per_week'),
            'max_full_days_per_year': data.get('max_full_days_per_year'),
            'duration_initial_months': data.get('duration_initial_months'),
            'extension_rules': data.get('extension_rules'),
            'key_documents': data.get('key_documents', []),
            'source_urls': data.get('source_urls', []),
            'last_verified_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        
        result = db.immigration_rules.insert_one(rule_doc)
        rule_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Immigration rule created successfully',
            'rule': rule_doc
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating immigration rule: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/immigration-rules/<rule_id>', methods=['PUT'])
@require_admin
def update_immigration_rule(rule_id):
    """PUT /api/admin/immigration-rules/<id> - Update immigration rule"""
    try:
        if not ObjectId.is_valid(rule_id):
            return jsonify({'error': 'Invalid rule ID', 'code': 'INVALID_ID'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'code': 'INVALID_DATA'}), 400
        
        db = get_db()
        
        # Don't allow updating _id
        update_data = {k: v for k, v in data.items() if k != '_id'}
        update_data['last_verified_at'] = datetime.utcnow()
        
        result = db.immigration_rules.update_one(
            {'_id': ObjectId(rule_id)},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Rule not found', 'code': 'NOT_FOUND'}), 404
        
        updated_rule = db.immigration_rules.find_one({'_id': ObjectId(rule_id)})
        updated_rule['_id'] = str(updated_rule['_id'])
        
        return jsonify({
            'message': 'Immigration rule updated successfully',
            'rule': updated_rule
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating immigration rule: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/immigration-rules/<rule_id>', methods=['DELETE'])
@require_admin
def delete_immigration_rule(rule_id):
    """DELETE /api/admin/immigration-rules/<id> - Delete immigration rule"""
    try:
        if not ObjectId.is_valid(rule_id):
            return jsonify({'error': 'Invalid rule ID', 'code': 'INVALID_ID'}), 400
        
        db = get_db()
        result = db.immigration_rules.delete_one({'_id': ObjectId(rule_id)})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Rule not found', 'code': 'NOT_FOUND'}), 404
        
        return jsonify({'message': 'Immigration rule deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting immigration rule: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/stats', methods=['GET'])
@require_admin
def get_stats():
    """GET /api/admin/stats - Get basic statistics"""
    try:
        db = get_db()
        
        stats = {
            'universities': db.universities.count_documents({}),
            'programmes': db.programmes.count_documents({}),
            'immigration_rules': db.immigration_rules.count_documents({}),
            'student_profiles': db.student_profiles.count_documents({}),
            'documents': db.documents.count_documents({}),
            'assessments': db.assessments.count_documents({}),
            'counseling_sessions': db.counseling_sessions.count_documents({}),
            'embeddings': db.embeddings.count_documents({}),
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

