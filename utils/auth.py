"""
Authentication and authorization utilities
"""
from flask import session, request
from functools import wraps
from config import Config

def get_user_id():
    """
    Get current user ID from session
    Returns session-based user_id for anonymous users
    """
    return session.get('user_id')

def require_admin(f):
    """
    Decorator to require admin authentication
    Checks session for admin login status
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            # Try basic auth
            auth = request.authorization
            if auth and auth.username == Config.ADMIN_USERNAME and auth.password == Config.ADMIN_PASSWORD:
                session['admin_logged_in'] = True
            else:
                return {'error': 'Admin authentication required', 'code': 'AUTH_REQUIRED'}, 401
        return f(*args, **kwargs)
    return decorated_function

