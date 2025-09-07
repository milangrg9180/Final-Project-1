# blueprints/main.py - Main blueprint for general routes
from flask import Blueprint, render_template, request, session
from utils.database import get_db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Home page."""
    return render_template('index.html')

@main_bp.route('/internships')
def internships():
    """Browse all internships."""
    conn = get_db()
    cursor = conn.cursor()
    
    search = request.args.get('search', '')
    if search:
        cursor.execute('''
            SELECT internships.*, users.name as company_name 
            FROM internships 
            JOIN users ON internships.company_id = users.id 
            WHERE internships.title LIKE ? OR internships.description LIKE ?
        ''', (f'%{search}%', f'%{search}%'))
    else:
        cursor.execute('''
            SELECT internships.*, users.name as company_name 
            FROM internships 
            JOIN users ON internships.company_id = users.id
        ''')
    
    internships = cursor.fetchall()
    
    # Check if user has applied to each internship
    applied_internships = []
    if 'user_id' in session and session['role'] == 'student':
        cursor.execute("SELECT internship_id FROM applications WHERE student_id=?", (session['user_id'],))
        applied_internships = [row['internship_id'] for row in cursor.fetchall()]
    
    return render_template('internships.html', internships=internships, 
                           applied_internships=applied_internships, search=search)
