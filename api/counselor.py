"""
Counselor API endpoints
Handles counseling sessions, messages, and action plans
"""
from flask import Blueprint, request, jsonify
from models.mongo import get_db
from utils.auth import get_user_id
from services.counselor import generate_counselor_response
from bson import ObjectId
from datetime import datetime
import logging
import uuid

bp = Blueprint('counselor', __name__)
logger = logging.getLogger(__name__)

@bp.route('/sessions', methods=['POST'])
def create_session():
    """
    POST /api/counselor/sessions
    Create a new counseling session
    
    Request body (optional):
    - title: session title
    - purpose: session purpose (initial_planning, programme_shortlist, visa_prep, etc.)
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        data = request.get_json() or {}
        
        db = get_db()
        
        session_doc = {
            'user_id': user_id,
            'title': data.get('title', 'New Counseling Session'),
            'purpose': data.get('purpose', 'general'),
            'summary': '',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = db.counseling_sessions.insert_one(session_doc)
        session_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Session created successfully',
            'session': session_doc
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/sessions', methods=['GET'])
def list_sessions():
    """
    GET /api/counselor/sessions
    List all counseling sessions for current user
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        db = get_db()
        sessions = list(db.counseling_sessions.find(
            {'user_id': user_id}
        ).sort('created_at', -1))
        
        for session in sessions:
            session['_id'] = str(session['_id'])
        
        return jsonify({'sessions': sessions}), 200
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """
    GET /api/counselor/sessions/<id>
    Get session metadata
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        if not ObjectId.is_valid(session_id):
            return jsonify({'error': 'Invalid session ID', 'code': 'INVALID_ID'}), 400
        
        db = get_db()
        session = db.counseling_sessions.find_one({
            '_id': ObjectId(session_id),
            'user_id': user_id
        })
        
        if not session:
            return jsonify({'error': 'Session not found', 'code': 'NOT_FOUND'}), 404
        
        session['_id'] = str(session['_id'])
        return jsonify({'session': session}), 200
        
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/sessions/<session_id>/messages', methods=['GET'])
def get_messages(session_id):
    """
    GET /api/counselor/sessions/<id>/messages
    Get all messages for a session
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        if not ObjectId.is_valid(session_id):
            return jsonify({'error': 'Invalid session ID', 'code': 'INVALID_ID'}), 400
        
        db = get_db()
        
        # Verify session belongs to user
        session = db.counseling_sessions.find_one({
            '_id': ObjectId(session_id),
            'user_id': user_id
        })
        if not session:
            return jsonify({'error': 'Session not found', 'code': 'NOT_FOUND'}), 404
        
        # Get messages
        messages = list(db.counseling_messages.find(
            {'session_id': session_id}
        ).sort('created_at', 1))
        
        for msg in messages:
            msg['_id'] = str(msg['_id'])
        
        return jsonify({'messages': messages}), 200
        
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/sessions/<session_id>/message', methods=['POST'])
def send_message(session_id):
    """
    POST /api/counselor/sessions/<id>/message
    Send a message and get AI counselor response
    
    Request body:
    - message: user's message text
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        if not ObjectId.is_valid(session_id):
            return jsonify({'error': 'Invalid session ID', 'code': 'INVALID_ID'}), 400
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message required', 'code': 'MISSING_MESSAGE'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty', 'code': 'EMPTY_MESSAGE'}), 400
        
        db = get_db()
        
        # Verify session belongs to user
        session = db.counseling_sessions.find_one({
            '_id': ObjectId(session_id),
            'user_id': user_id
        })
        if not session:
            return jsonify({'error': 'Session not found', 'code': 'NOT_FOUND'}), 404
        
        # Get user profile and assessment
        profile = db.student_profiles.find_one({'user_id': user_id})
        assessment = db.assessments.find_one(
            {'user_id': user_id},
            sort=[('created_at', -1)]
        )
        plan = db.counseling_plans.find_one({
            'user_id': user_id,
            'session_id': session_id
        })
        
        # Get conversation history
        history = list(db.counseling_messages.find(
            {'session_id': session_id}
        ).sort('created_at', -1).limit(10))
        history.reverse()  # Oldest first
        
        # Remove ObjectIds for service
        if profile:
            profile.pop('_id', None)
        if assessment:
            assessment.pop('_id', None)
        if plan:
            plan.pop('_id', None)
        for msg in history:
            msg.pop('_id', None)
        
        # Store user message
        user_msg_doc = {
            'session_id': session_id,
            'user_id': user_id,
            'sender': 'user',
            'message_type': 'question',
            'message_text': user_message,
            'created_at': datetime.utcnow()
        }
        db.counseling_messages.insert_one(user_msg_doc)
        
        # Generate AI response
        counselor_response = generate_counselor_response(
            session_id=session_id,
            user_message=user_message,
            user_profile=profile,
            assessment=assessment,
            plan=plan,
            history=history
        )
        
        # Store assistant message
        assistant_msg_doc = {
            'session_id': session_id,
            'user_id': user_id,
            'sender': 'assistant',
            'message_type': 'answer',
            'message_text': counselor_response['response'],
            'created_at': datetime.utcnow()
        }
        db.counseling_messages.insert_one(assistant_msg_doc)
        
        # Update session
        db.counseling_sessions.update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {'updated_at': datetime.utcnow()}}
        )
        
        # Handle plan updates
        if counselor_response.get('plan_updates'):
            update_action_plan(user_id, session_id, counselor_response['plan_updates'])
        
        # Handle profile updates from conversation
        profile_updates = counselor_response.get('profile_updates', {})
        if profile_updates:
            try:
                # Update profile automatically from conversation
                existing_profile = db.student_profiles.find_one({'user_id': user_id})
                
                # Handle preferred_cities if it's a string, convert to list
                if 'preferred_cities' in profile_updates:
                    if isinstance(profile_updates['preferred_cities'], str):
                        profile_updates['preferred_cities'] = [c.strip() for c in profile_updates['preferred_cities'].split(',') if c.strip()]
                
                if existing_profile:
                    # Update existing profile
                    update_data = {}
                    for key, value in profile_updates.items():
                        if value:  # Only update non-empty values
                            update_data[key] = value
                    
                    if update_data:
                        update_data['updated_at'] = datetime.utcnow()
                        db.student_profiles.update_one(
                            {'user_id': user_id},
                            {'$set': update_data}
                        )
                        logger.info(f"Auto-updated profile with: {list(update_data.keys())}")
                else:
                    # Create new profile with extracted data
                    profile_doc = {
                        'user_id': user_id,
                        **profile_updates,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                    db.student_profiles.insert_one(profile_doc)
                    logger.info("Created new profile from conversation")
            except Exception as e:
                logger.error(f"Error updating profile from conversation: {e}")
        
        return jsonify({
            'message': 'Message sent and response generated',
            'user_message': {
                'text': user_message,
                'sender': 'user',
                'created_at': user_msg_doc['created_at'].isoformat()
            },
            'assistant_message': {
                'text': counselor_response['response'],
                'sender': 'assistant',
                'sources': counselor_response.get('sources', []),
                'created_at': assistant_msg_doc['created_at'].isoformat()
            },
            'profile_updated': bool(profile_updates)
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

def update_action_plan(user_id, session_id, plan_updates):
    """Update action plan based on counselor suggestions"""
    try:
        db = get_db()
        plan = db.counseling_plans.find_one({
            'user_id': user_id,
            'session_id': session_id
        })
        
        if plan_updates.get('new_steps'):
            if not plan:
                # Create new plan
                plan = {
                    'user_id': user_id,
                    'session_id': session_id,
                    'country_target': 'DE',
                    'plan_steps': [],
                    'last_updated_at': datetime.utcnow()
                }
                db.counseling_plans.insert_one(plan)
                plan_id = plan['_id']
            else:
                plan_id = plan['_id']
            
            # Add new steps
            for new_step in plan_updates['new_steps']:
                new_step['step_id'] = str(uuid.uuid4())
                new_step.setdefault('status', 'pending')
                db.counseling_plans.update_one(
                    {'_id': plan_id},
                    {'$push': {'plan_steps': new_step}}
                )
        
        # Update last_updated_at
        if plan:
            db.counseling_plans.update_one(
                {'_id': plan_id if 'plan_id' in locals() else plan['_id']},
                {'$set': {'last_updated_at': datetime.utcnow()}}
            )
            
    except Exception as e:
        logger.warning(f"Error updating action plan: {e}")

@bp.route('/plan', methods=['GET'])
def get_action_plan():
    """
    GET /api/counselor/plan
    Get current user's action plan (for current session or latest)
    Query param: session_id (optional)
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        session_id = request.args.get('session_id')
        
        db = get_db()
        query = {'user_id': user_id}
        if session_id and ObjectId.is_valid(session_id):
            query['session_id'] = session_id
        
        plan = db.counseling_plans.find_one(
            query,
            sort=[('last_updated_at', -1)]
        )
        
        if not plan:
            return jsonify({'plan': None}), 200
        
        plan['_id'] = str(plan['_id'])
        return jsonify({'plan': plan}), 200
        
    except Exception as e:
        logger.error(f"Error getting action plan: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/plan/update', methods=['POST'])
def update_plan():
    """
    POST /api/counselor/plan/update
    Update action plan steps
    
    Request body:
    - session_id: session ID (optional)
    - action: 'add', 'update', 'remove'
    - step: step object with step_id, title, status, due_date, notes
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'error': 'Action required', 'code': 'INVALID_DATA'}), 400
        
        action = data.get('action')
        session_id = data.get('session_id')
        step = data.get('step', {})
        
        db = get_db()
        
        # Find or create plan
        query = {'user_id': user_id}
        if session_id and ObjectId.is_valid(session_id):
            query['session_id'] = session_id
        
        plan = db.counseling_plans.find_one(query)
        
        if not plan:
            # Create new plan
            plan = {
                'user_id': user_id,
                'session_id': session_id,
                'country_target': 'DE',
                'plan_steps': [],
                'created_at': datetime.utcnow(),
                'last_updated_at': datetime.utcnow()
            }
            result = db.counseling_plans.insert_one(plan)
            plan['_id'] = result.inserted_id
        else:
            plan['_id'] = plan['_id']
        
        # Perform action
        if action == 'add':
            step['step_id'] = step.get('step_id') or str(uuid.uuid4())
            step.setdefault('status', 'pending')
            db.counseling_plans.update_one(
                {'_id': plan['_id']},
                {'$push': {'plan_steps': step}}
            )
        elif action == 'update':
            step_id = step.get('step_id')
            if not step_id:
                return jsonify({'error': 'step_id required for update', 'code': 'INVALID_DATA'}), 400
            
            # Remove step_id from update data
            update_data = {k: v for k, v in step.items() if k != 'step_id'}
            
            # Update specific step in array
            db.counseling_plans.update_one(
                {'_id': plan['_id'], 'plan_steps.step_id': step_id},
                {'$set': {f'plan_steps.$': step}}
            )
        elif action == 'remove':
            step_id = step.get('step_id')
            if not step_id:
                return jsonify({'error': 'step_id required for remove', 'code': 'INVALID_DATA'}), 400
            
            db.counseling_plans.update_one(
                {'_id': plan['_id']},
                {'$pull': {'plan_steps': {'step_id': step_id}}}
            )
        else:
            return jsonify({'error': 'Invalid action', 'code': 'INVALID_ACTION'}), 400
        
        # Update last_updated_at
        db.counseling_plans.update_one(
            {'_id': plan['_id']},
            {'$set': {'last_updated_at': datetime.utcnow()}}
        )
        
        # Return updated plan
        updated_plan = db.counseling_plans.find_one({'_id': plan['_id']})
        updated_plan['_id'] = str(updated_plan['_id'])
        
        return jsonify({
            'message': 'Plan updated successfully',
            'plan': updated_plan
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating plan: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

