"""
Main routes for serving HTML pages
"""
from flask import render_template

def register_routes(app):
    """Register all route handlers"""
    
    @app.route('/')
    def index():
        """Home page"""
        return render_template('index.html')
    
    @app.route('/universities')
    def universities_page():
        """Universities listing page"""
        return render_template('universities.html')
    
    @app.route('/universities/<university_id>')
    def university_detail_page(university_id):
        """University detail page"""
        return render_template('university_detail.html', university_id=university_id)
    
    @app.route('/programmes')
    def programmes_page():
        """Programmes listing page"""
        return render_template('programmes.html')
    
    @app.route('/immigration')
    def immigration_page():
        """Immigration helper page"""
        return render_template('immigration.html')
    
    @app.route('/profile')
    def profile_page():
        """Student profile page"""
        return render_template('profile.html')
    
    @app.route('/counselor')
    def counselor_page():
        """AI counselor page"""
        return render_template('counselor.html')
    
    @app.route('/admin')
    def admin_page():
        """Admin dashboard page"""
        return render_template('admin.html')

