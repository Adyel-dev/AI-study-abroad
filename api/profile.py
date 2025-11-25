"""
Student Profile API endpoints
Handles profile creation, updates, and retrieval
"""
from flask import Blueprint, request, jsonify
from models.mongo import get_db
from utils.auth import get_user_id
from datetime import datetime
import logging

bp = Blueprint('profile', __name__)
logger = logging.getLogger(__name__)

@bp.route('/profile', methods=['GET'])
def get_profile():
    """
    GET /api/profile
    Get current user's profile
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        db = get_db()
        profile = db.student_profiles.find_one({'user_id': user_id})
        
        if not profile:
            return jsonify({'profile': None}), 200
        
        profile['_id'] = str(profile['_id'])
        return jsonify({'profile': profile}), 200
        
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/profile', methods=['POST'])
def create_or_update_profile():
    """
    POST /api/profile
    Create or update current user's profile
    
    Expected fields:
    - name (optional)
    - nationality
    - country_of_residence
    - highest_education_level
    - highest_education_field
    - gpa_or_marks
    - english_level
    - german_level (optional)
    - desired_study_level
    - desired_field
    - preferred_cities (array)
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'code': 'INVALID_DATA'}), 400
        
        # Validate required fields
        required_fields = ['nationality', 'country_of_residence', 'highest_education_level', 
                          'desired_study_level']
        missing_fields = [f for f in required_fields if f not in data or not data[f]]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'code': 'MISSING_FIELDS'
            }), 400
        
        db = get_db()
        
        # Prepare profile document
        profile_doc = {
            'user_id': user_id,
            'name': data.get('name', '').strip() or None,
            'nationality': data.get('nationality', '').strip(),
            'country_of_residence': data.get('country_of_residence', '').strip(),
            'highest_education_level': data.get('highest_education_level', '').strip(),
            'highest_education_field': data.get('highest_education_field', '').strip() or None,
            'gpa_or_marks': data.get('gpa_or_marks', '').strip() or None,
            'english_level': data.get('english_level', '').strip() or None,
            'german_level': data.get('german_level', '').strip() or None,
            'desired_study_level': data.get('desired_study_level', '').strip(),
            'desired_field': data.get('desired_field', '').strip() or None,
            'preferred_cities': data.get('preferred_cities', []),
            'updated_at': datetime.utcnow()
        }
        
        # Check if profile exists
        existing = db.student_profiles.find_one({'user_id': user_id})
        
        if existing:
            # Update existing profile
            profile_doc['created_at'] = existing.get('created_at', datetime.utcnow())
            db.student_profiles.update_one(
                {'user_id': user_id},
                {'$set': profile_doc}
            )
            profile_doc['_id'] = str(existing['_id'])
            message = 'Profile updated successfully'
        else:
            # Create new profile
            profile_doc['created_at'] = datetime.utcnow()
            result = db.student_profiles.insert_one(profile_doc)
            profile_doc['_id'] = str(result.inserted_id)
            message = 'Profile created successfully'
        
        return jsonify({
            'message': message,
            'profile': profile_doc
        }), 200
        
    except Exception as e:
        logger.error(f"Error saving profile: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

