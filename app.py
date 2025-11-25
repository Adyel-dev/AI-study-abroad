"""
Main Flask application entry point for Study in Germany AI Counselor
"""
from flask import Flask, session
import os
import uuid
import logging
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from api import universities, programmes, immigration, profile, documents, assessments, chat, counselor, admin
    app.register_blueprint(universities.bp, url_prefix='/api')
    app.register_blueprint(programmes.bp, url_prefix='/api')
    app.register_blueprint(immigration.bp, url_prefix='/api/immigration')
    app.register_blueprint(profile.bp, url_prefix='/api')
    app.register_blueprint(documents.bp, url_prefix='/api')
    app.register_blueprint(assessments.bp, url_prefix='/api')
    app.register_blueprint(chat.bp, url_prefix='/api')
    app.register_blueprint(counselor.bp, url_prefix='/api/counselor')
    app.register_blueprint(admin.bp, url_prefix='/api/admin')
    
    # Register routes
    from routes import register_routes
    register_routes(app)
    
    # Initialize database with initial data if empty
    # This runs automatically on startup to populate empty database
    def init_database_background():
        """Initialize database in background thread if collections are empty"""
        try:
            import time
            # Small delay to ensure MongoDB connection is ready
            time.sleep(2)
            from scripts.init_data import initialize_database_if_empty
            initialized = initialize_database_if_empty()
            if initialized:
                logger.info("✓ Database initialized with initial data")
            else:
                logger.info("✓ Database already contains data - skipping initialization")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    import threading
    init_thread = threading.Thread(target=init_database_background, daemon=True)
    init_thread.start()
    logger.info("Database initialization check started in background thread")
    
    # Initialize scheduler if enabled
    if app.config['ENABLE_SCHEDULER']:
        try:
            from jobs.scheduler import init_scheduler
            init_scheduler(app)
            logger.info("Background scheduler initialized")
        except Exception as e:
            logger.warning(f"Could not initialize scheduler: {e}")
    
    @app.before_request
    def before_request():
        """Ensure user_id exists in session"""
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        if 'session_id' not in session:
            session['session_id'] = session.get('user_id')
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {'status': 'ok'}, 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # For gunicorn
    app = create_app()

