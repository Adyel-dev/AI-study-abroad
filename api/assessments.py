"""
Assessments API endpoints
Handles feasibility assessment requests
"""
from flask import Blueprint, request, jsonify
from models.mongo import get_db
from utils.auth import get_user_id
from services.assessment import run_assessment
from datetime import datetime
import logging

bp = Blueprint('assessments', __name__)
logger = logging.getLogger(__name__)

@bp.route('/assessments/run', methods=['POST'])
def run_assessment_endpoint():
    """
    POST /api/assessments/run
    Run feasibility assessment for current user
    Uses profile and documents from database
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        db = get_db()
        
        # Get user profile
        profile = db.student_profiles.find_one({'user_id': user_id})
        if not profile:
            return jsonify({
                'error': 'Profile not found. Please create a profile first.',
                'code': 'PROFILE_NOT_FOUND'
            }), 400
        
        # Remove MongoDB ObjectId
        profile.pop('_id', None)
        
        # Get user documents
        documents = list(db.documents.find({'user_id': user_id}))
        for doc in documents:
            doc.pop('_id', None)
            doc.pop('storage_path', None)  # Don't include file path
        
        # Get immigration rules (optional)
        immigration_rules = list(db.immigration_rules.find({'country_code': 'DE'}))
        
        # Run assessment
        assessment_result = run_assessment(profile, documents, immigration_rules)
        
        # Add metadata
        assessment_doc = {
            'user_id': user_id,
            'profile_snapshot': profile,
            'documents_summary': {
                'has_transcript': any(doc.get('document_type') == 'transcript' for doc in documents),
                'has_degree_certificate': any(doc.get('document_type') == 'degree_certificate' for doc in documents),
                'has_language_certificate': any(doc.get('document_type') == 'language_certificate' for doc in documents),
                'has_cv': any(doc.get('document_type') == 'CV' for doc in documents),
                'has_sop': any(doc.get('document_type') == 'SOP' for doc in documents),
                'total_documents': len(documents)
            },
            **assessment_result,
            'created_at': datetime.utcnow()
        }
        
        # Save assessment to database
        result = db.assessments.insert_one(assessment_doc)
        assessment_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Assessment completed successfully',
            'assessment': assessment_doc
        }), 200
        
    except Exception as e:
        logger.error(f"Error running assessment: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/assessments/latest', methods=['GET'])
def get_latest_assessment():
    """
    GET /api/assessments/latest
    Get latest assessment for current user
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        db = get_db()
        assessment = db.assessments.find_one(
            {'user_id': user_id},
            sort=[('created_at', -1)]
        )
        
        if not assessment:
            return jsonify({'assessment': None}), 200
        
        assessment['_id'] = str(assessment['_id'])
        return jsonify({'assessment': assessment}), 200
        
    except Exception as e:
        logger.error(f"Error getting latest assessment: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

