"""
Immigration API endpoints
Handles immigration rules and visa advice
"""
from flask import Blueprint, request, jsonify
from models.mongo import get_db
from utils.auth import get_user_id
from bson import ObjectId
import logging

bp = Blueprint('immigration', __name__)
logger = logging.getLogger(__name__)

IMMIGRATION_DISCLAIMER = "This is informational only and not legal advice. Always confirm with official embassies/authorities."

@bp.route('/rules', methods=['GET'])
def get_immigration_rules():
    """
    GET /api/immigration/rules
    Get all immigration rules for Germany
    Optional query params:
    - visa_type: filter by visa type
    - country_code: filter by country (default: DE)
    """
    try:
        db = get_db()
        
        country_code = request.args.get('country_code', 'DE').upper()
        visa_type = request.args.get('visa_type', '').strip()
        
        query = {'country_code': country_code}
        if visa_type:
            query['visa_type'] = {'$regex': visa_type, '$options': 'i'}
        
        rules = list(db.immigration_rules.find(query).sort('visa_type', 1))
        
        for rule in rules:
            rule['_id'] = str(rule['_id'])
        
        return jsonify({
            'rules': rules,
            'disclaimer': IMMIGRATION_DISCLAIMER
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting immigration rules: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/advice', methods=['POST'])
def get_immigration_advice():
    """
    POST /api/immigration/advice
    Get personalized immigration advice based on user input
    
    Request body:
    - nationality: user's nationality
    - planned_level: planned study level (Bachelor, Master, PhD, etc.)
    - has_admission_letter: boolean
    - scholarship: boolean or details
    - language_of_instruction: English or German (optional)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'code': 'INVALID_DATA'}), 400
        
        nationality = data.get('nationality', '').strip()
        planned_level = data.get('planned_level', '').strip()
        has_admission_letter = data.get('has_admission_letter', False)
        scholarship = data.get('scholarship', False)
        language_of_instruction = data.get('language_of_instruction', '').strip()
        
        if not nationality or not planned_level:
            return jsonify({
                'error': 'Missing required fields: nationality, planned_level',
                'code': 'MISSING_FIELDS'
            }), 400
        
        db = get_db()
        
        # Determine visa type needed
        visa_type = None
        if planned_level.lower() in ['language course', 'studienkolleg']:
            visa_type = 'Language Course / Studienkolleg'
        elif planned_level.lower() in ['bachelor', 'master', 'phd', 'doctorate']:
            visa_type = 'National Study Visa (D-Study)'
        
        # Get relevant immigration rules
        query = {'country_code': 'DE'}
        if visa_type:
            query['visa_type'] = {'$regex': visa_type, '$options': 'i'}
        
        rules = list(db.immigration_rules.find(query))
        
        # Build advice response
        advice = {
            'nationality': nationality,
            'planned_level': planned_level,
            'recommended_visa_types': [],
            'summary': '',
            'key_requirements': [],
            'funds_required': None,
            'work_allowed': None,
            'duration': None,
            'key_documents': [],
            'source_urls': [],
            'disclaimer': IMMIGRATION_DISCLAIMER
        }
        
        if rules:
            # Use first matching rule for now (can be enhanced with nationality-specific logic)
            rule = rules[0]
            
            advice['recommended_visa_types'] = [rule.get('visa_type', 'Study Visa')]
            
            # Funds requirement
            if rule.get('min_funds_year_eur'):
                advice['funds_required'] = {
                    'annual': rule['min_funds_year_eur'],
                    'monthly': rule.get('min_funds_month_eur', rule['min_funds_year_eur'] / 12),
                    'blocked_account': True
                }
            
            # Work permissions
            if rule.get('work_hours_per_week') is not None:
                advice['work_allowed'] = {
                    'hours_per_week': rule['work_hours_per_week'],
                    'full_days_per_year': rule.get('max_full_days_per_year')
                }
            
            # Duration
            if rule.get('duration_initial_months'):
                advice['duration'] = {
                    'initial_months': rule['duration_initial_months'],
                    'extension_rules': rule.get('extension_rules', 'Can be extended based on study duration')
                }
            
            # Documents
            advice['key_documents'] = rule.get('key_documents', [])
            
            # Source URLs
            advice['source_urls'] = rule.get('source_urls', [])
            
            # Build summary text
            summary_parts = [
                f"For studying {planned_level} in Germany, you will typically need a {rule.get('visa_type', 'Study Visa')}."
            ]
            
            if advice['funds_required']:
                summary_parts.append(
                    f"You will need to show proof of sufficient funds: approximately €{advice['funds_required']['annual']:.0f} per year (usually in a blocked account)."
                )
            
            if has_admission_letter:
                summary_parts.append("Since you have an admission letter, you can apply for the visa directly.")
            else:
                summary_parts.append("You will need to obtain an admission letter from a German university before applying for the visa.")
            
            if language_of_instruction == 'German' and not rule.get('language_requirements'):
                summary_parts.append("Note: German language proficiency may be required (typically C1 level).")
            elif language_of_instruction == 'English':
                summary_parts.append("For English-taught programmes, you may need to demonstrate English proficiency (IELTS/TOEFL).")
            
            if scholarship:
                summary_parts.append("If you have a scholarship, check if it covers the financial requirements or if additional funds are needed.")
            
            advice['summary'] = ' '.join(summary_parts)
            
            # Key requirements list
            advice['key_requirements'] = [
                'Valid passport',
                'Admission letter from German university',
                'Proof of financial means (blocked account)',
                'Health insurance',
                'Language proficiency certificate (if required)'
            ]
            
            if rule.get('key_documents'):
                advice['key_requirements'].extend(rule['key_documents'])
        
        else:
            # Fallback if no rules found
            advice['summary'] = f"For studying {planned_level} in Germany, you will need to apply for a student visa. Please consult the German embassy in your country for specific requirements based on your nationality ({nationality})."
            advice['recommended_visa_types'] = ['Student Visa (D-Study)']
            advice['key_requirements'] = [
                'Valid passport',
                'Admission letter',
                'Proof of financial means',
                'Health insurance'
            ]
        
        return jsonify(advice), 200
        
    except Exception as e:
        logger.error(f"Error getting immigration advice: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

