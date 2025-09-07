# blueprints/auth.py - Authentication blueprint
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.database import get_db
from utils.auth import hash_password, check_password

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        name = request.form.get('name', '')
        
        if not email or not password or not role:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('auth.register'))
        
        hashed_pw = hash_password(password)
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (email, password, role, name) VALUES (?, ?, ?, ?)",
                           (email, hashed_pw, role, name))
            conn.commit()
            
            # If student, create empty profile
            if role == 'student':
                user_id = cursor.lastrowid
                cursor.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
                conn.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            flash('Email already registered', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        
        if user and check_password(password, user['password']):
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['role'] = user['role']
            session['name'] = user['name']
            
            if user['role'] == 'student':
                # Check if student has CV
                cursor.execute("SELECT * FROM cvs WHERE user_id=?", (user['id'],))
                cv = cursor.fetchone()
                
                if not cv:
                    # No CV exists, redirect to CV creation
                    return redirect(url_for('cv.create'))
                
                # Redirect to dashboard (skills are now managed through CV)
                return redirect(url_for('student.dashboard'))
            elif user['role'] == 'company':
                return redirect(url_for('company.dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('main.home'))
