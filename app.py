from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, json
from flask_cors import CORS
import sqlite3
import os
import datetime
import time

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'supersecretkey_trackademic'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection(database='trackademic.db'):
    """Get database connection for trackademic database"""
    try:
        conn = sqlite3.connect(database, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_social_db_connection():
    """Get database connection for social platform database"""
    return get_db_connection('social.db')

def init_databases():
    """Initialize both databases"""
    
    # Initialize Trackademic Database
    conn = get_db_connection('trackademic.db')
    cursor = conn.cursor()
    
    # Trackademic tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL UNIQUE,
        subject_code TEXT UNIQUE,
        credit_hours INTEGER DEFAULT 3,
        task_description TEXT DEFAULT ''
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS timetable (
        timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        day INTEGER NOT NULL,
        time_slot TEXT NOT NULL,
        task_description TEXT DEFAULT '',
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
        FOREIGN KEY (user_id) REFERENCES trackademic_users(user_id),
        UNIQUE(user_id, day, time_slot)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trackademic_users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gpa (
            gpa_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trimester TEXT NOT NULL,
            gpa REAL NOT NULL CHECK (gpa >= 0.0 AND gpa <= 4.0),
            total_credits INTEGER DEFAULT 0,
            total_grade_points REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES trackademic_users(user_id) ON DELETE CASCADE,
            UNIQUE(user_id, trimester)
        )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file BLOB,
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Initialize Social Database
    db = get_social_db_connection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER DEFAULT 0
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            username TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            folder_name TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS saved_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            post_id INTEGER,
            folder_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id),
            FOREIGN KEY(folder_id) REFERENCES folders(id)
        )
    """)
    db.commit()
    db.close()
    
    # Check if admin exists, if not create one
    create_admin_user()

def create_admin_user():
    """Create admin user if it doesn't exist"""
    try:
        # Check trackademic database
        conn = get_db_connection()
        admin = conn.execute(
            "SELECT * FROM trackademic_users WHERE email = ?", 
            ('admin@login.com',)
        ).fetchone()
        
        if not admin:
            conn.execute(
                "INSERT INTO trackademic_users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                ('admin', 'admin@login.com', 'admin3.142', 1)
            )
            conn.commit()
        
        conn.close()
        
        # Check social database
        db = get_social_db_connection()
        social_admin = db.execute(
            "SELECT * FROM users WHERE email = ?", 
            ('admin@login.com',)
        ).fetchone()
        
        if not social_admin:
            db.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                ('admin', 'admin@login.com', 'admin3.142', 1)
            )
            db.commit()
        
        db.close()
        
    except Exception as e:
        print(f"Error creating admin user: {e}")

init_databases()

# ============ API ENDPOINTS ============
@app.route('/api/subjects', methods=['GET'])
def api_get_subjects():
    """API endpoint to get all subjects for the calculator"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        subjects = conn.execute('''
            SELECT subject_id as id, 
                   subject_name as name, 
                   subject_code as code, 
                   credit_hours as credits 
            FROM subjects 
            ORDER BY subject_code
        ''').fetchall()
        
        conn.close()
        
        # Convert to list of dictionaries
        subjects_list = []
        for subject in subjects:
            subjects_list.append({
                'id': subject['id'],
                'name': subject['name'],
                'code': subject['code'],
                'credits': subject['credits']
            })
        
        return jsonify({
            'success': True,
            'subjects': subjects_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/save-trimester', methods=['POST'])
def api_save_trimester():
    """API endpoint to save trimester GPA data - FIXED VERSION"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Get the current session user_id (from social database)
        social_user_id = session['user_id']
        
        # First, check if user exists in trackademic_users
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        # Try to find trackademic user by email first (most reliable)
        trackademic_user_id = None
        
        # Get user info from social database to find by email
        social_db = get_social_db_connection()
        social_user = social_db.execute(
            'SELECT username, email FROM users WHERE id = ?',
            (social_user_id,)
        ).fetchone()
        social_db.close()
        
        if social_user:
            # Try to find trackademic user by email
            track_user = conn.execute(
                'SELECT user_id FROM trackademic_users WHERE email = ?',
                (social_user['email'],)
            ).fetchone()
            
            if track_user:
                trackademic_user_id = track_user['user_id']
                print(f"Found trackademic user by email: {trackademic_user_id}")
        
        # If not found by email, try to find by username
        if not trackademic_user_id and social_user:
            track_user = conn.execute(
                'SELECT user_id FROM trackademic_users WHERE username = ?',
                (social_user['username'],)
            ).fetchone()
            
            if track_user:
                trackademic_user_id = track_user['user_id']
                print(f"Found trackademic user by username: {trackademic_user_id}")
        
        # If still not found, create a new trackademic user
        if not trackademic_user_id and social_user:
            try:
                cursor = conn.execute(
                    'INSERT INTO trackademic_users (username, email, password, is_admin) VALUES (?, ?, ?, ?)',
                    (social_user['username'], social_user['email'], 'default_password', 0)
                )
                conn.commit()
                trackademic_user_id = cursor.lastrowid
                print(f"Created new trackademic user: {trackademic_user_id}")
                
                # Store in session for future use
                session['trackademic_user_id'] = trackademic_user_id
            except sqlite3.IntegrityError as e:
                # User might have been created by another process
                track_user = conn.execute(
                    'SELECT user_id FROM trackademic_users WHERE email = ?',
                    (social_user['email'],)
                ).fetchone()
                if track_user:
                    trackademic_user_id = track_user['user_id']
                    session['trackademic_user_id'] = trackademic_user_id
                else:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'error': f'Error creating trackademic user: {str(e)}'
                    }), 500
        
        if not trackademic_user_id:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Could not find or create trackademic user record'
            }), 404
        
        # Now use the trackademic_user_id to save GPA data
        user_id = trackademic_user_id
        
        # Validate required fields
        trimester_name = data.get('trimester', 'Trimester 1')
        gpa_value = float(data.get('gpa', 0.0))
        total_credits = int(data.get('total_credits', 0))
        total_grade_points = float(data.get('total_grade_points', 0.0))
        
        # Validate GPA range
        if not (0.0 <= gpa_value <= 4.0):
            conn.close()
            return jsonify({
                'success': False, 
                'error': 'GPA must be between 0.0 and 4.0'
            }), 400
        
        # Check if trimester already exists for this user
        existing = conn.execute(
            'SELECT * FROM gpa WHERE user_id = ? AND trimester = ?', 
            (user_id, trimester_name)
        ).fetchone()
        
        if existing:
            # Update existing record
            conn.execute(
                '''UPDATE gpa 
                   SET gpa = ?, total_credits = ?, total_grade_points = ?, created_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND trimester = ?''',
                (gpa_value, total_credits, total_grade_points, user_id, trimester_name)
            )
            action = 'updated'
        else:
            # Insert new record
            conn.execute(
                '''INSERT INTO gpa 
                   (user_id, trimester, gpa, total_credits, total_grade_points) 
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, trimester_name, gpa_value, total_credits, total_grade_points)
            )
            action = 'saved'
        
        conn.commit()
        
        # Verify the save was successful
        saved = conn.execute(
            'SELECT * FROM gpa WHERE user_id = ? AND trimester = ?', 
            (user_id, trimester_name)
        ).fetchone()
        
        conn.close()
        
        if saved:
            return jsonify({
                'success': True,
                'message': f'Trimester {trimester_name} {action} successfully',
                'data': {
                    'user_id': user_id,
                    'trimester': trimester_name,
                    'gpa': gpa_value,
                    'total_credits': total_credits,
                    'total_grade_points': total_grade_points
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save trimester data'
            }), 500
            
    except Exception as e:
        # Log the full error for debugging
        print(f"Error in api_save_trimester: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@app.route('/api/cgpa-history', methods=['GET'])
def api_get_cgpa_history():
    """API endpoint to get CGPA history for current user"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get trackademic user ID
        social_user_id = session['user_id']
        conn = get_db_connection()
        
        # Find trackademic user by email from social database
        social_db = get_social_db_connection()
        social_user = social_db.execute(
            'SELECT email FROM users WHERE id = ?',
            (social_user_id,)
        ).fetchone()
        social_db.close()
        
        trackademic_user_id = None
        if social_user:
            track_user = conn.execute(
                'SELECT user_id FROM trackademic_users WHERE email = ?',
                (social_user['email'],)
            ).fetchone()
            if track_user:
                trackademic_user_id = track_user['user_id']
        
        if not trackademic_user_id:
            conn.close()
            return jsonify({
                'success': True,
                'history': [],
                'message': 'No GPA data found for user'
            })
        
        # Get GPA data for the trackademic user
        gpa_data = conn.execute('''
            SELECT gpa_id as id, 
                   trimester, 
                   gpa,
                   total_credits,
                   total_grade_points,
                   created_at as date
            FROM gpa 
            WHERE user_id = ?
            ORDER BY trimester
        ''', (trackademic_user_id,)).fetchall()
        
        conn.close()
        
        # Convert to list of dictionaries
        history_list = []
        for item in gpa_data:
            history_list.append({
                'id': item['id'],
                'semester': item['trimester'],
                'date': item['date'] or 'Not Available',
                'gpa': float(item['gpa']),
                'totalCredits': item['total_credits'] or 0,
                'totalGradePoints': item['total_grade_points'] or 0
            })
        
        return jsonify({
            'success': True,
            'history': history_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
# ============ COMMON ROUTES ============
@app.route('/')
def home():
    """Main landing page"""
    if 'user_id' in session:
        # Check if user is admin
        if 'is_admin' in session and session['is_admin'] == 1:
            return redirect('/admin/home')
        elif 'app_mode' in session and session['app_mode'] == 'social':
            return redirect('/social/dashboard')
        else:
            return redirect('/trackademic')
    return render_template('home.html')

@app.route('/set-app-mode/<mode>')
def set_app_mode(mode):
    """Set the current application mode"""
    if 'user_id' not in session:
        return redirect('/login')
    
    session['app_mode'] = mode
    if mode == 'social':
        return redirect('/social/dashboard')
    else:
        return redirect('/trackademic')

# ============ AUTHENTICATION ROUTES ============
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login page"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        app_choice = request.form.get('app_choice', 'trackademic')
        
        # Check if this is admin login
        if email == 'admin@login.com':
            # Try social database first
            db = get_social_db_connection()
            cursor = db.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
            user = cursor.fetchone()
            db.close()
            
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['app_mode'] = app_choice
                session['is_admin'] = 1  # Mark as admin
                # NEW: Store trackademic user ID and email
                session['trackademic_user_id'] = user['id']
                session['email'] = email
                return redirect('/admin/home')
            
            # Try trackademic database
            conn = get_db_connection()
            track_user = conn.execute(
                "SELECT * FROM trackademic_users WHERE email=? AND password=?",
                (email, password)
            ).fetchone()
            conn.close()
            
            if track_user:
                session['user_id'] = track_user['user_id']
                session['username'] = track_user['username']
                session['app_mode'] = app_choice
                session['is_admin'] = 1  # Mark as admin
                # NEW: Store trackademic user ID and email
                session['trackademic_user_id'] = track_user['user_id']
                session['email'] = email
                return redirect('/admin/home')
        
        # Regular user login
        # Try social database first
        db = get_social_db_connection()
        cursor = db.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        db.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['app_mode'] = app_choice
            session['is_admin'] = 0  # Regular user
            
            # NEW: Store trackademic user ID and email in session
            conn = get_db_connection()
            track_user = conn.execute(
                "SELECT user_id FROM trackademic_users WHERE email=?",
                (email,)
            ).fetchone()
            conn.close()
            
            if track_user:
                session['trackademic_user_id'] = track_user['user_id']
                session['email'] = email  # Store email for GPA lookups
            else:
                # If not found, use social user ID as fallback
                session['trackademic_user_id'] = user['id']
                session['email'] = email
            
            if app_choice == 'social':
                return redirect('/social/dashboard')
            else:
                # Also check trackademic user table
                conn = get_db_connection()
                track_user = conn.execute(
                    "SELECT * FROM trackademic_users WHERE email=? AND password=?",
                    (email, password)
                ).fetchone()
                conn.close()
                
                if not track_user:
                    # Create trackademic user record if it doesn't exist
                    conn = get_db_connection()
                    conn.execute(
                        "INSERT OR IGNORE INTO trackademic_users (username, email, password) VALUES (?, ?, ?)",
                        (user['username'], email, password)
                    )
                    conn.commit()
                    conn.close()
                
                return redirect('/trackademic')
        
        # Try trackademic database
        conn = get_db_connection()
        track_user = conn.execute(
            "SELECT * FROM trackademic_users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()
        
        if track_user:
            session['user_id'] = track_user['user_id']
            session['username'] = track_user['username']
            session['app_mode'] = app_choice
            session['is_admin'] = 0  # Regular user
            
            # NEW: Store trackademic user ID and email
            session['trackademic_user_id'] = track_user['user_id']
            session['email'] = email
            
            if app_choice == 'social':
                # Create social user record if it doesn't exist
                db = get_social_db_connection()
                db.execute(
                    "INSERT OR IGNORE INTO users (username, email, password) VALUES (?, ?, ?)",
                    (track_user['username'], email, password)
                )
                db.commit()
                db.close()
                return redirect('/social/dashboard')
            else:
                return redirect('/trackademic')
        
        return render_template('login.html', error="Wrong email or password.")
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Unified signup page"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password', '')
        
        # Add password confirmation check
        if password != confirm_password:
            return render_template('signup.html', error="Passwords do not match.")
        
        # Prevent using admin email
        if email == 'admin@login.com':
            return render_template('signup.html', error="This email is reserved for admin.")
        
        trackademic_conn = None
        social_db = None
        
        try:
            # Create user in trackademic database
            trackademic_conn = get_db_connection()  # trackademic.db
            trackademic_conn.execute(
                "INSERT INTO trackademic_users (username, email, password, is_admin) VALUES (?, ?, ?, 0)",
                (username, email, password)
            )
            trackademic_conn.commit()
            
            # Get the trackademic user ID
            track_user = trackademic_conn.execute(
                "SELECT user_id FROM trackademic_users WHERE email=?",
                (email,)
            ).fetchone()
            trackademic_user_id = track_user['user_id']
            
            # Create user in social database
            social_db = get_social_db_connection()  # social.db
            social_db.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, 0)",
                (username, email, password)
            )
            social_db.commit()
            
            # Get user ID from social DB
            cursor = social_db.execute("SELECT * FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            
            if not user:
                return render_template('signup.html', error="Error creating account. Please try again.")
            
            # Set session variables
            session['user_id'] = user['id']
            session['username'] = username
            session['app_mode'] = 'trackademic'  # Default to trackademic
            session['is_admin'] = 0  # Regular user
            
            # NEW: Store trackademic user ID and email in session
            session['trackademic_user_id'] = trackademic_user_id
            session['email'] = email
            
            # Redirect to trackademic by default
            return redirect('/trackademic')
                
        except sqlite3.IntegrityError:
            return render_template('signup.html', error="Email already exists.")
        except Exception as e:
            print(f"Signup error: {e}")
            return render_template('signup.html', error=f"Error creating account: {str(e)}")
        finally:
            # Ensure connections are closed
            if trackademic_conn:
                trackademic_conn.close()
            if social_db:
                social_db.close()
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Logout from both systems"""
    session.clear()
    return redirect('/login')

# ============ ADMIN HOME PAGE ============
@app.route('/admin/home')
def admin_home():
    """Admin-only home page"""
    if 'user_id' not in session or 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/login')
    
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Dashboard</title>
        <link rel="stylesheet" href="/static/home-styles.css">
    </head>
    <body class="trackademic-body trackademic-home">  <!-- Added trackademic-home class here -->
        <div class="home-container">
            <div class="home-header">
                <h1>Admin Dashboard</h1>
                <p>Welcome back, ''' + session.get('username', 'Admin') + '''!</p>
            </div>
            
            <div class="welcome-section">
                <h2>Trackademic Administration</h2>
                <p>Manage all aspects of the Trackademic platform from this dashboard</p>
            </div>
            
            <div class="apps-grid">
                <div class="admin-section">
                    <h3 style="color: #667eea; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px;">Applications:</h3>
                    <div class="apps-grid" style="grid-template-columns: 1fr; gap: 15px; padding: 0;">
                        <a href="/trackademic/timetable" class="app-card">
                            <div class="app-icon">📅</div>
                            <h3>Timetable</h3>
                            <p>Manage and edit the academic timetable</p>
                        </a>
                        
                        <a href="/trackademic/calculator" class="app-card">
                            <div class="app-icon">🧮</div>
                            <h3>GPA Calculator</h3>
                            <p>Access the GPA calculator and view GPA data</p>
                        </a>
                        
                        <a href="/social/dashboard" class="app-card">
                            <div class="app-icon">👥</div>
                            <h3>Social Dashboard</h3>
                            <p>Access the social platform dashboard</p>
                        </a>
                    </div>
                </div>
                
                <div class="admin-section">
                    <h3 style="color: #667eea; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px;">View Data:</h3>
                    <div class="apps-grid" style="grid-template-columns: 1fr; gap: 15px; padding: 0;">
                        <a href="/trackademic/subjects" class="app-card">
                            <div class="app-icon">📚</div>
                            <h3>All Subjects</h3>
                            <p>View, edit, and manage all subjects in the system</p>
                        </a>
                        
                        <a href="/trackademic/user" class="app-card">
                            <div class="app-icon">👤</div>
                            <h3>All Users</h3>
                            <p>View and manage user accounts and permissions</p>
                        </a>
                        
                        <a href="/trackademic/gpa" class="app-card">
                            <div class="app-icon">📊</div>
                            <h3>GPA Data</h3>
                            <p>View and manage GPA records and history</p>
                        </a>
                    </div>
                </div>
                
                <div class="admin-section">
                    <h3 style="color: #667eea; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px;">Reset Data:</h3>
                    <div class="apps-grid" style="grid-template-columns: 1fr; gap: 15px; padding: 0;">
                        <a href="/trackademic/create-subjects-db" class="app-card" style="background: #fff5f5; border-color: #fc8181;">
                            <div class="app-icon" style="color: #fc8181;">🔄</div>
                            <h3>Reset Subjects</h3>
                            <p>Reset the subjects database with sample data</p>
                        </a>
                        
                        <a href="/trackademic/create-user-db" class="app-card" style="background: #fff5f5; border-color: #fc8181;">
                            <div class="app-icon" style="color: #fc8181;">🔄</div>
                            <h3>Reset Users</h3>
                            <p>Reset the user database with sample data</p>
                        </a>
                        
                        <a href="/trackademic/create-gpa-db" class="app-card" style="background: #fff5f5; border-color: #fc8181;">
                            <div class="app-icon" style="color: #fc8181;">🔄</div>
                            <h3>Reset GPA</h3>
                            <p>Reset the GPA database with sample data</p>
                        </a>
                        
                        <a href="/trackademic/edit_timetable" class="app-card" style="background: #fff5f5; border-color: #fc8181;">
                            <div class="app-icon" style="color: #fc8181;">🔄</div>
                            <h3>Reset Timetable</h3>
                            <p>Clear and reset the timetable (Enter Edit Mode)</p>
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="actions-section">
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
        </div>
        <style>
            .admin-section {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 20px;
            }
            
            .admin-section h3 {
                font-size: 1.2rem;
                color: #667eea;
            }
            
            .apps-grid {
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            }
            
            @media (max-width: 768px) {
                .apps-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </body>
    </html>
    '''

@app.route('/trackademic')
def trackademic_home():
    """Trackademic home page for regular users"""
    if 'user_id' not in session:
        return redirect('/login')
    
    # If admin, redirect to admin home
    if 'is_admin' in session and session['is_admin'] == 1:
        return redirect('/admin/home')
    
    session['app_mode'] = 'trackademic'
    
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trackademic Home</title>
        <link rel="stylesheet" href="/static/home-styles.css">
    </head>
    <body class="trackademic-body trackademic-home">  <!-- Added trackademic-home class here -->
        <div class="home-container">
            <div class="home-header">
                <h1>Trackademic</h1>
                <p>Study Planner & GPA Calculator</p>
            </div>
            
            <div class="welcome-section">
                <h2>Welcome back, ''' + session.get('username', 'Student') + '''!</h2>
                <p>Manage your academic schedule, calculate your GPA, and organize your notes in one place.</p>
            </div>
            
            <div class="apps-grid">
                <a href="/trackademic/timetable" class="app-card">
                    <div class="app-icon">📅</div>
                    <h3>Timetable</h3>
                    <p>View and manage your weekly class schedule and tasks</p>
                </a>
                
                <a href="/trackademic/calculator" class="app-card">
                    <div class="app-icon">🧮</div>
                    <h3>GPA Calculator</h3>
                    <p>Calculate your GPA and track your academic performance</p>
                </a>
                
                <a href="/social/dashboard" class="app-card">
                    <div class="app-icon">👥</div>
                    <h3>Social Dashboard</h3>
                    <p>Connect with classmates and share resources</p>
                </a>
            </div>
            
            <div class="actions-section">
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
        </div>
    </body>
    </html>
    '''

# ============ TRACKADEMIC SUBJECT ROUTES ============
@app.route('/trackademic/subjects')
def list_subjects():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        conn = get_db_connection()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
        conn.close()
        
        if not subjects:
            return '<h1>No subjects found.</h1><p><a href="/trackademic/create-subjects-db">Reset subjects database</a></p>'
        
        html = '<h1>All Subjects</h1>'
        html += '<p><a href="/trackademic/add-subject-form-db">+ Add New Subject</a></p>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>Code</th><th>Subject Name</th><th>Credit Hours</th><th>Actions</th></tr>'
        
        for subject in subjects:
            html += f'<tr>'
            html += f'<td>{subject["subject_id"]}</td>'
            html += f'<td>{subject["subject_code"]}</td>'
            html += f'<td>{subject["subject_name"]}</td>'
            html += f'<td>{subject["credit_hours"]}</td>'
            html += f'<td>'
            html += f'<a href="/trackademic/edit-subject/{subject["subject_id"]}" style="border-radius: 3px; margin: 0 5px;">Edit</a>'
            html += f'<a href="/trackademic/delete-subject/{subject["subject_id"]}" style="border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this subject?\')">Delete</a>'
            html += f'</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/admin/home">Back to Admin Home</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error accessing database: {str(e)}</h1>'

@app.route('/trackademic/add-subject-form-db', methods=['GET', 'POST'])
def add_subject_form_db():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    if request.method == 'POST':
        subject_name = request.form['subject_name']
        subject_code = request.form['subject_code']
        credit_hours = request.form['credit_hours']
        
        try:
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO subjects (subject_name, subject_code, credit_hours) VALUES (?, ?, ?)',
                (subject_name, subject_code, credit_hours)
            )
            conn.commit()
            conn.close()
            return redirect('/trackademic/subjects')
        except Exception as e:
            return f'<h1>Failed to add subject: {str(e)}</h1><p><a href="/trackademic/add-subject-form-db">Try again</a></p>'
    
    return '''
    <h1>Add New Subject</h1>
    <form method="POST" style="max-width: 500px;">
        <div style="margin: 10px 0;">
            <label for="subject_name">Subject Name:</label><br>
            <input type="text" id="subject_name" name="subject_name" required style="width: 100%; padding: 8px; margin: 5px 0;">
        </div>
        <div style="margin: 10px 0;">
            <label for="subject_code">Subject Code:</label><br>
            <input type="text" id="subject_code" name="subject_code" required style="width: 100%; padding: 8px; margin: 5px 0;">
        </div>
        <div style="margin: 10px 0;">
            <label for="credit_hours">Credit Hours:</label><br>
            <input type="number" id="credit_hours" name="credit_hours" value="3" min="1" max="6" style="width: 100%; padding: 8px; margin: 5px 0;">
        </div>
        <div style="margin: 10px 0;">
            <input type="submit" value="Add Subject" style="padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
            <a href="/trackademic/subjects" style="background: #ccc; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Cancel</a>
        </div>
    </form>
    '''

@app.route('/trackademic/edit-subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        subject_name = request.form['subject_name']
        subject_code = request.form['subject_code']
        credit_hours = request.form['credit_hours']
        
        try:
            conn.execute(
                'UPDATE subjects SET subject_name = ?, subject_code = ?, credit_hours = ? WHERE subject_id = ?',
                (subject_name, subject_code, credit_hours, subject_id)
            )
            conn.commit()
            conn.close()
            return redirect('/trackademic/subjects')
        except Exception as e:
            conn.close()
            return f'<h1>Error updating subject!</h1><p><a href="/trackademic/edit-subject/{subject_id}">Try again</a></p>'
    
    subject = conn.execute('SELECT * FROM subjects WHERE subject_id = ?', (subject_id,)).fetchone()
    conn.close()
    
    if not subject:
        return '<h1>Subject not found</h1><p><a href="/trackademic/subjects">Back to subjects</a></p>'
    
    return f'''
    <h1>Edit Subject</h1>
    <form method="POST" style="max-width: 500px;">
        <div style="margin: 10px 0;">
            <label for="subject_name">Subject Name:</label><br>
            <input type="text" id="subject_name" name="subject_name" value="{subject['subject_name']}" required style="width: 100%; padding: 8px; margin: 5px 0;">
        </div>
        <div style="margin: 10px 0;">
            <label for="subject_code">Subject Code:</label><br>
            <input type="text" id="subject_code" name="subject_code" value="{subject['subject_code']}" required style="width: 100%; padding: 8px; margin: 5px 0;">
        </div>
        <div style="margin: 10px 0;">
            <label for="credit_hours">Credit Hours:</label><br>
            <input type="number" id="credit_hours" name="credit_hours" value="{subject['credit_hours']}" min="1" max="6" style="width: 100%; padding: 8px; margin: 5px 0;">
        </div>
        <div style="margin: 10px 0;">
            <input type="submit" value="Update Subject" style="background: #2196F3; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
            <a href="/trackademic/subjects" style="background: #ccc; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Cancel</a>
        </div>
    </form>
    '''

@app.route('/trackademic/delete-subject/<int:subject_id>')
def delete_subject(subject_id):
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM subjects WHERE subject_id = ?', (subject_id,))
        conn.commit()
        conn.close()
        return f'<h1>Subject deleted successfully!</h1><p><a href="/trackademic/subjects">Back to subjects</a></p>'
    except Exception as e:
        return f'<h1>Error deleting subject!</h1><p><a href="/trackademic/subjects">Back to subjects</a></p>'

# ============ TRACKADEMIC USER ROUTES ============
@app.route('/trackademic/user')
def list_user():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM trackademic_users ORDER BY user_id').fetchall()
        conn.close()
        
        if not user:
            return '<h1>No user found.</h1><p><a href="/trackademic/reset-users">Reset users database</a></p>'
        
        html = '<h1>All Users</h1>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>Username</th><th>Email</th><th>Password</th><th>Is Admin</th><th>Actions</th></tr>'
        
        for users in user:
            html += f'<tr>'
            html += f'<td>{users["user_id"]}</td>'
            html += f'<td>{users["username"]}</td>'
            html += f'<td>{users["email"]}</td>'
            html += f'<td>{users["password"]}</td>'
            html += f'<td>{"Yes" if users["is_admin"] == 1 else "No"}</td>'
            html += f'<td>'
            html += f'<a href="/trackademic/delete-user/{users["user_id"]}" style="border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this user?\')">Delete</a>'
            html += f'</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/admin/home">Back to Admin Home</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error accessing database: {str(e)}</h1>'

@app.route('/trackademic/delete-user/<int:user_id>')
def delete_user(user_id):
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM trackademic_users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        return f'<h1>User deleted successfully!</h1><p><a href="/trackademic/user">Back to users</a></p>'
    except Exception as e:
        return f'<h1>Error deleting user! {str(e)}</h1><p><a href="/trackademic/user">Back to users</a></p>'

# ============ CALCULATOR HELPER FUNCTIONS ============
def calculate_gpa_server(subjects):
    """Server-side GPA calculation"""
    GRADE_SCALE = {
        'A+': 4.00,
        'A': 4.00,
        'A-': 3.67,
        'B+': 3.33,
        'B': 3.00,
        'B-': 2.67,
        'C+': 2.33,
        'C': 2.00,
        'C-': 1.67,
        'D+': 1.33,
        'D': 1.00,
        'F': 0.00
    }
    
    total_credits = 0
    total_grade_points = 0
    subjects_with_grades = 0
    subjects_without_grades = 0
    
    for subject in subjects:
        grade = subject.get('grade', '')
        credits = subject.get('credits', 0)
        
        if grade and grade in GRADE_SCALE:
            grade_points = GRADE_SCALE[grade]
            subject_grade_points = credits * grade_points
            
            total_credits += credits
            total_grade_points += subject_grade_points
            subjects_with_grades += 1
        else:
            subjects_without_grades += 1
    
    gpa = total_grade_points / total_credits if total_credits > 0 else 0
    
    return {
        'total_credits': total_credits,
        'total_grade_points': total_grade_points,
        'gpa': gpa,
        'subjects_with_grades': subjects_with_grades,
        'subjects_without_grades': subjects_without_grades,
        'total_subjects': len(subjects)
    }

def calculate_cgpa_server(history):
    """Server-side CGPA calculation"""
    if not history:
        return 0.0
    
    total_cumulative_credits = 0
    total_cumulative_grade_points = 0
    
    for semester in history:
        total_cumulative_credits += semester.get('total_credits', 0)
        total_cumulative_grade_points += semester.get('total_grade_points', 0)
    
    cgpa = total_cumulative_grade_points / total_cumulative_credits if total_cumulative_credits > 0 else 0
    return cgpa

# ============ CALCULATOR ROUTE ============
@app.route('/trackademic/calculator', methods=['GET', 'POST'])
def calculator():
    """Trackademic GPA Calculator - Server-side version"""
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Make session variables user-specific
    current_trimester_key = f'calculator_current_trimester_{user_id}'
    current_subjects_key = f'calculator_current_subjects_{user_id}'
    
    # Check if we need to clear old session data from other users
    for key in list(session.keys()):
        if key.startswith('calculator_') and not key.endswith(str(user_id)):
            # This is session data from a different user, remove it
            session.pop(key, None)
    
    # Initialize session variables if they don't exist
    if current_trimester_key not in session:
        session[current_trimester_key] = 1
    if current_subjects_key not in session:
        session[current_subjects_key] = []
    
    # REMOVE: Session-based CGPA history storage
    # We'll load from database instead

    # Get current state from session
    current_trimester = session.get(current_trimester_key, 1)
    current_subjects = session.get(current_subjects_key, [])
    
    # NEW: Load CGPA history from database instead of session
    cgpa_history = []
    try:
        # Find trackademic user ID
        social_user_id = session['user_id']
        conn = get_db_connection()
        
        # Get user info from social database
        social_db = get_social_db_connection()
        social_user = social_db.execute(
            'SELECT email FROM users WHERE id = ?',
            (social_user_id,)
        ).fetchone()
        social_db.close()
        
        if social_user:
            # Find trackademic user by email
            track_user = conn.execute(
                'SELECT user_id FROM trackademic_users WHERE email = ?',
                (social_user['email'],)
            ).fetchone()
            
            if track_user:
                trackademic_user_id = track_user['user_id']
                
                # Get GPA history from database
                gpa_records = conn.execute('''
                    SELECT gpa_id as id, 
                           trimester, 
                           gpa,
                           total_credits,
                           total_grade_points,
                           created_at as date
                    FROM gpa 
                    WHERE user_id = ?
                    ORDER BY trimester
                ''', (trackademic_user_id,)).fetchall()
                
                # Convert database records to CGPA history format
                for record in gpa_records:
                    # Extract trimester number from trimester name
                    trimester_name = record['trimester']
                    trimester_number = 1
                    if ' ' in trimester_name:
                        try:
                            trimester_number = int(trimester_name.split()[1])
                        except:
                            pass
                    
                    cgpa_history.append({
                        'semester': trimester_name,
                        'trimester_number': trimester_number,
                        'date': record['date'] or datetime.datetime.now().strftime('%Y-%m-%d'),
                        'gpa': float(record['gpa']),
                        'total_credits': record['total_credits'] or 0,
                        'total_grade_points': record['total_grade_points'] or 0,
                        'subjects': []  # Subjects not stored in database, but we don't need them for display
                    })
        
        conn.close()
    except Exception as e:
        print(f"Error loading CGPA history from database: {e}")
    
    # Grade scale for template
    GRADE_SCALE = {
        'A+': 4.00,
        'A': 4.00,
        'A-': 3.67,
        'B+': 3.33,
        'B': 3.00,
        'B-': 2.67,
        'C+': 2.33,
        'C': 2.00,
        'C-': 1.67,
        'D+': 1.33,
        'D': 1.00,
        'F': 0.00
    }
    
    # Handle POST requests
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'change_trimester':
            new_trimester = request.form.get('current_trimester')
            if new_trimester and new_trimester.isdigit():
                new_trimester = int(new_trimester)
                if new_trimester != current_trimester:
                    session[current_trimester_key] = new_trimester
                    session[current_subjects_key] = []
                    return redirect('/trackademic/calculator')
        
        elif action == 'add_subject':
            subject_id = request.form.get('subject_to_add')
            if subject_id:
                subject_id = int(subject_id)
                # Get all subjects from database
                conn = get_db_connection()
                subject_data = conn.execute('''
                    SELECT subject_id as id, 
                           subject_name as name, 
                           subject_code as code, 
                           credit_hours as credits 
                    FROM subjects 
                    WHERE subject_id = ?
                ''', (subject_id,)).fetchone()
                conn.close()
                
                if subject_data:
                    # Check if subject already exists in current trimester
                    existing_ids = [s['id'] for s in current_subjects]
                    if subject_id not in existing_ids:
                        subject_with_grade = {
                            'id': subject_data['id'],
                            'name': subject_data['name'],
                            'code': subject_data['code'],
                            'credits': subject_data['credits'],
                            'grade': '',
                            'trimester': current_trimester
                        }
                        current_subjects.append(subject_with_grade)
                        session[current_subjects_key] = current_subjects
        
        elif action.startswith('remove_subject_'):
            try:
                subject_id = int(action.split('_')[-1])
                current_subjects = [s for s in current_subjects if s['id'] != subject_id]
                session[current_subjects_key] = current_subjects
            except (IndexError, ValueError):
                pass
        
        elif action.startswith('update_grade_'):
            try:
                subject_id = int(action.split('_')[-1])
                grade = request.form.get(f'grade_{subject_id}', '')
                
                # Update the grade in current_subjects
                for subject in current_subjects:
                    if subject['id'] == subject_id:
                        subject['grade'] = grade
                        break
                session[current_subjects_key] = current_subjects
            except (IndexError, ValueError):
                pass
        
        elif action == 'save_trimester':
            # Calculate current GPA
            current_gpa_data = calculate_gpa_server(current_subjects)

            # Check if all subjects have grades
            if current_gpa_data['subjects_without_grades'] == 0 and current_subjects:
                # Prepare semester data
                semester_data = {
                    'semester': f'Trimester {current_trimester}',
                    'trimester_number': current_trimester,
                    'date': datetime.datetime.now().strftime('%Y-%m-%d'),
                    'total_credits': current_gpa_data['total_credits'],
                    'total_grade_points': current_gpa_data['total_grade_points'],
                    'gpa': current_gpa_data['gpa'],
                    'subjects': current_subjects.copy()
                }
        
                # Also save to database with user_id
                try:
                    # Get the correct user_id for trackademic database
                    conn = get_db_connection()
    
                    # First, check if user exists in trackademic_users
                    trackademic_user = conn.execute(
                        'SELECT user_id FROM trackademic_users WHERE email = ?',
                        (session.get('email', ''),)
                    ).fetchone()
    
                    if not trackademic_user:
                        # Try to find by username
                        trackademic_user = conn.execute(
                            'SELECT user_id FROM trackademic_users WHERE username = ?',
                            (session.get('username', ''),)
                        ).fetchone()
    
                    if trackademic_user:
                        user_id = trackademic_user['user_id']
                    else:
                        # Create a new trackademic user entry
                        # Get user info from social database if available
                        social_db = get_social_db_connection()
                        social_user = social_db.execute(
                            'SELECT username, email FROM users WHERE id = ?',
                            (session['user_id'],)
                        ).fetchone()
                        social_db.close()

                        if social_user:
                            conn.execute(
                                'INSERT INTO trackademic_users (username, email, password, is_admin) VALUES (?, ?, ?, ?)',
                                (social_user['username'], social_user['email'], 'default_password', 0)
                            )
                            conn.commit()
                            user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                        else:
                            # Fallback - create with session data
                            conn.execute(
                                'INSERT INTO trackademic_users (username, email, password, is_admin) VALUES (?, ?, ?, ?)',
                                (session['username'], f"{session['username']}@example.com", 'default_password', 0)
                            )
                            conn.commit()
                            user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

                    # Now save the GPA data with the correct user_id
                    trimester_name = f'Trimester {current_trimester}'

                    # Check if trimester already exists for this user
                    existing = conn.execute(
                        'SELECT * FROM gpa WHERE user_id = ? AND trimester = ?',
                        (user_id, trimester_name)
                    ).fetchone()

                    if existing:
                        # Update existing
                        conn.execute(
                            '''UPDATE gpa 
                               SET gpa = ?, total_credits = ?, total_grade_points = ?, created_at = CURRENT_TIMESTAMP 
                               WHERE user_id = ? AND trimester = ?''',
                            (current_gpa_data['gpa'], current_gpa_data['total_credits'], 
                             current_gpa_data['total_grade_points'], user_id, trimester_name)
                        )
                        action_msg = 'updated'
                    else:
                        # Insert new
                        conn.execute(
                            '''INSERT INTO gpa (user_id, trimester, gpa, total_credits, total_grade_points) 
                               VALUES (?, ?, ?, ?, ?)''',
                            (user_id, trimester_name, current_gpa_data['gpa'], 
                             current_gpa_data['total_credits'], current_gpa_data['total_grade_points'])
                        )
                        action_msg = 'saved'

                    conn.commit()
                    print(f"GPA saved for user_id={user_id}, trimester={trimester_name}, GPA={current_gpa_data['gpa']:.2f}")

                    # Reload CGPA history from database after saving
                    # Get updated history
                    gpa_records = conn.execute('''
                        SELECT gpa_id as id, 
                               trimester, 
                               gpa,
                               total_credits,
                               total_grade_points,
                               created_at as date
                        FROM gpa 
                        WHERE user_id = ?
                        ORDER BY trimester
                    ''', (user_id,)).fetchall()
                    
                    # Update cgpa_history with fresh data from database
                    cgpa_history.clear()
                    for record in gpa_records:
                        trimester_name = record['trimester']
                        trimester_number = 1
                        if ' ' in trimester_name:
                            try:
                                trimester_number = int(trimester_name.split()[1])
                            except:
                                pass
                        
                        cgpa_history.append({
                            'semester': trimester_name,
                            'trimester_number': trimester_number,
                            'date': record['date'] or datetime.datetime.now().strftime('%Y-%m-%d'),
                            'gpa': float(record['gpa']),
                            'total_credits': record['total_credits'] or 0,
                            'total_grade_points': record['total_grade_points'] or 0,
                            'subjects': []
                        })

                except Exception as e:
                    print(f"Error saving GPA to database: {e}")
                    import traceback
                    traceback.print_exc()
                    action_msg = 'error'
                finally:
                    if 'conn' in locals():
                        conn.close()

                # Only reset and advance if save was successful
                if action_msg in ['saved', 'updated']:
                    # Reset current trimester and advance to next
                    session[current_subjects_key] = []
                    if current_trimester < 6:
                        session[current_trimester_key] = current_trimester + 1

                    flash(f'Trimester {current_trimester} {action_msg} successfully! GPA: {current_gpa_data["gpa"]:.2f}', 'success')
                else:
                    flash(f'Error saving trimester {current_trimester}. Please try again.', 'error')
                    
                return redirect('/trackademic/calculator')
            else:
                flash('Please select grades for all subjects before saving.', 'error')

        elif action == 'reset_trimester':
            session[current_subjects_key] = []
        
        elif action == 'clear_history':
            # NEW: Clear history from database instead of session
            try:
                # Find trackademic user ID
                social_user_id = session['user_id']
                conn = get_db_connection()
                
                # Get user info from social database
                social_db = get_social_db_connection()
                social_user = social_db.execute(
                    'SELECT email FROM users WHERE id = ?',
                    (social_user_id,)
                ).fetchone()
                social_db.close()
                
                if social_user:
                    # Find trackademic user by email
                    track_user = conn.execute(
                        'SELECT user_id FROM trackademic_users WHERE email = ?',
                        (social_user['email'],)
                    ).fetchone()
                    
                    if track_user:
                        # Delete all GPA records for this user
                        conn.execute(
                            'DELETE FROM gpa WHERE user_id = ?',
                            (track_user['user_id'],)
                        )
                        conn.commit()
                        
                conn.close()
                cgpa_history = []  # Clear local history
                flash('All CGPA history has been cleared.', 'success')
            except Exception as e:
                print(f"Error clearing history from database: {e}")
                flash('Error clearing history. Please try again.', 'error')
        
        elif action.startswith('remove_history_'):
            try:
                trimester_number = int(action.split('_')[-1])
                # NEW: Remove from database instead of session
                try:
                    # Find trackademic user ID
                    social_user_id = session['user_id']
                    conn = get_db_connection()
                    
                    # Get user info from social database
                    social_db = get_social_db_connection()
                    social_user = social_db.execute(
                        'SELECT email FROM users WHERE id = ?',
                        (social_user_id,)
                    ).fetchone()
                    social_db.close()
                    
                    if social_user:
                        # Find trackademic user by email
                        track_user = conn.execute(
                            'SELECT user_id FROM trackademic_users WHERE email = ?',
                            (social_user['email'],)
                        ).fetchone()
                        
                        if track_user:
                            # Delete specific trimester
                            trimester_name = f'Trimester {trimester_number}'
                            conn.execute(
                                'DELETE FROM gpa WHERE user_id = ? AND trimester = ?',
                                (track_user['user_id'], trimester_name)
                            )
                            conn.commit()
                            
                            # Update local history
                            cgpa_history = [s for s in cgpa_history if s['trimester_number'] != trimester_number]
                    
                    conn.close()
                    flash(f'Trimester {trimester_number} removed from history.', 'success')
                except Exception as e:
                    print(f"Error removing history from database: {e}")
                    flash('Error removing trimester. Please try again.', 'error')
            except (IndexError, ValueError):
                pass
        
        # Refresh current values after POST (except CGPA history which comes from DB)
        current_trimester = session.get(current_trimester_key, 1)
        current_subjects = session.get(current_subjects_key, [])
    
    # Get all subjects from database for the dropdown
    conn = get_db_connection()
    all_subjects = conn.execute('''
        SELECT subject_id as id, 
               subject_name as name, 
               subject_code as code, 
               credit_hours as credits 
        FROM subjects 
        ORDER BY subject_code
    ''').fetchall()
    conn.close()
    
    # Calculate current GPA
    current_gpa_data = calculate_gpa_server(current_subjects)
    
    # Calculate overall CGPA from database history
    overall_cgpa = calculate_cgpa_server(cgpa_history)
    
    # Render the calculator template with all data
    return render_template('Calculator.html',
                         all_subjects=all_subjects,
                         current_trimester=current_trimester,
                         current_subjects=current_subjects,
                         grade_scale=GRADE_SCALE,
                         current_gpa_data=current_gpa_data,
                         cgpa_history=cgpa_history,
                         overall_cgpa=overall_cgpa,
                         app_mode='trackademic')

# ============ TRACKADEMIC GPA ROUTES ============
@app.route('/trackademic/gpa')
def list_gpa():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        conn = get_db_connection()
        # Get GPA data with usernames
        gpa_data = conn.execute('''
            SELECT g.*, u.username, u.email 
            FROM gpa g 
            JOIN trackademic_users u ON g.user_id = u.user_id 
            ORDER BY g.user_id, g.trimester
        ''').fetchall()
        
        conn.close()
        
        if not gpa_data:
            return '<h1>No GPA data found.</h1><p><a href="/admin/home">Back to Admin Home</a></p>'
        
        html = '<h1>All GPA Data</h1>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>User</th><th>Email</th><th>Trimester</th><th>GPA</th><th>Credits</th><th>Actions</th></tr>'
        
        current_user = None
        for gpa in gpa_data:
            html += f'<tr>'
            html += f'<td>{gpa["gpa_id"]}</td>'
            html += f'<td>{gpa["username"]}</td>'
            html += f'<td>{gpa["email"]}</td>'
            html += f'<td>{gpa["trimester"]}</td>'
            html += f'<td>{gpa["gpa"]:.2f}</td>'
            html += f'<td>{gpa["total_credits"]}</td>'
            html += f'<td>'
            html += f'<a href="/trackademic/delete-gpa/{gpa["gpa_id"]}" style="border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this GPA record?\')">Delete</a>'
            html += f'</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/admin/home">Back to Admin Home</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error accessing database: {str(e)}</h1>'

@app.route('/trackademic/delete-gpa/<int:gpa_id>')
def delete_gpa(gpa_id):
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM gpa WHERE gpa_id = ?', (gpa_id,))
        conn.commit()
        conn.close()
        return f'<h1>GPA record deleted successfully!</h1><p><a href="/trackademic/gpa">Back to GPA Data</a></p>'
    except Exception as e:
        return f'<h1>Error deleting GPA! {str(e)}</h1><p><a href="/trackademic/gpa">Back to GPA Data</a></p>'

# ============ TRACKADEMIC DATABASE RESET ROUTES ============
@app.route('/trackademic/create-subjects-db')
def create_subjects_database_route():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        # Reset subjects table with sample data
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute('DELETE FROM subjects')
        
        # Add sample subjects from app (1).py
        subjects = [
            ('Introduction to Business Management', 'GNB1114', 4),
            ('Introduction to Computing Technologies', 'CCT1114', 4),
            ('Communicative English', 'LCE1113', 3),
            ('Mathematics I', 'CMT1114', 4),
            ('Problem Solving & Program Design', 'CSP1114', 4),
            ('Essential English', 'LEE1113', 3),
            ('Multimedia Fundamentals', 'CMF1114', 4),
            ('Mathematics II', 'CMT1124', 4),
            ('Critical Thinking', 'LCT1113', 3),
            ('Introduction to Digital Systems', 'CDS1114', 4),
            ('Academic English', 'LAE1113', 3),
            ('Mathematics III', 'CMT1134', 4),
            ('Principles of Physics', 'CPP1113', 3),
            ('Mini IT Project', 'CSP1123', 3),
        ]
        
        cursor.executemany(
            'INSERT INTO subjects (subject_name, subject_code, credit_hours) VALUES (?, ?, ?)',
            subjects
        )
        
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()
        return '''
        <h1>Subjects database reset successfully!</h1>
        <p><a href="/trackademic/subjects">View Subjects</a></p>
        <p><a href="/admin/home">Back to Admin Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating database! {str(e)}</h1>'

@app.route('/trackademic/create-notes-db')
def create_notes_database_route():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        # Reset notes table with sample data
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute('DELETE FROM notes')
        
        # Add sample notes from app (1).py
        notes = [
            (1, 1, 'business_notes.pdf', None),
            (2, 1, 'computing_notes.pdf', None),
            (3, 1, 'english_notes.pdf', None),
        ]
        
        cursor.executemany(
            'INSERT INTO notes (subject_id, user_id, file_name, file) VALUES (?, ?, ?, ?)',
            notes
        )
        
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()
        return '''
        <h1>Notes database reset successfully!</h1>
        <p><a href="/admin/home">Back to Admin Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating database! {str(e)}</h1>'

@app.route('/trackademic/create-gpa-db')
def create_gpa_database_route():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clear existing data but keep the table structure
        cursor.execute('DELETE FROM gpa')
        
        # Get admin user ID to assign sample data
        cursor.execute("SELECT user_id FROM trackademic_users WHERE email='admin@login.com'")
        admin_result = cursor.fetchone()
        
        if admin_result:
            admin_id = admin_result[0]
            
            # Add sample GPA data with admin user_id
            gpa_data = [
                (admin_id, 'Sample', 3.75, 12, 45.0),
            ]
            
            cursor.executemany(
                'INSERT INTO gpa (user_id, trimester, gpa, total_credits, total_grade_points) VALUES (?, ?, ?, ?, ?)',
                gpa_data
            )
        
        conn.commit()
        conn.close()
        return '''
        <h1>GPA database reset successfully!</h1>
        <p><a href="/trackademic/gpa">View GPA Data</a></p>
        <p><a href="/admin/home">Back to Admin Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating database! {str(e)}</h1>'
    
@app.route('/trackademic/create-user-db')
def create_user_database_route():
    # Check if user is admin
    if 'is_admin' not in session or session['is_admin'] != 1:
        return redirect('/trackademic')
    
    try:
        # Reset trackademic users table with sample data
        conn = get_db_connection()
        cursor = conn.cursor()
        current_user_id = session.get('user_id', None)
        
        cursor.execute('DELETE FROM trackademic_users')
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="trackademic_users"')
        
        # Add sample user from app (1).py
        user_data = [
            ('jiaxian0331', 'hoejiaxian@gmail.com', 'jiaxian0000', 0),
            ('admin', 'admin@login.com', 'admin3.142', 1)
        ]
        
        cursor.executemany(
            'INSERT INTO trackademic_users (username, email, password, is_admin) VALUES (?, ?, ?, ?)',
            user_data
        )
        
        conn.commit()
        conn.close()
        return '''
        <h1>User database reset successfully!</h1>
        <p><a href="/trackademic/user">View Users</a></p>
        <p><a href="/admin/home">Back to Admin Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating user database! {str(e)}</h1>'

# ============ TRACKADEMIC TIMETABLE ROUTES ============
@app.route('/trackademic/timetable')
def timetable():
    """View timetable in non-edit mode"""
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    conn = get_db_connection()
    timetable_data = conn.execute('''
        SELECT t.*, s.subject_name, s.subject_code, t.task_description
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        WHERE t.user_id = ?
        ORDER BY t.day, t.time_slot
    ''', (user_id,)).fetchall()
    
    schedule = {}
    for item in timetable_data:
        day = item['day']
        time_slot = item['time_slot']
        if day not in schedule:
            schedule[day] = {}
        schedule[day][time_slot] = {
            'subject_name': item['subject_name'],
            'subject_code': item['subject_code'],
            'time_slot': time_slot,
            'task_description': item['task_description'],
            'subject_id': item['subject_id'],
            'timetable_id': item['timetable_id']
        }
    
    # Get today's schedule
    today_schedule = get_today_schedule(user_id)
    
    # Get weekly summary
    weekly_summary = get_weekly_summary(user_id)
    
    conn.close()
    
    return render_template('timetable.html', schedule=schedule, edit_mode=False, 
                          today_schedule=today_schedule, weekly_summary=weekly_summary,
                          app_mode='trackademic')

@app.route('/trackademic/add_subject_form')
def add_subject_form():
    """Show form to add a subject to timetable - accessible to all users"""
    if 'user_id' not in session:
        return redirect('/login')
    
    day = int(request.args.get('day', 0))
    
    conn = get_db_connection()
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
    conn.close()
    
    return render_template('add_subject.html', 
                          subjects=subjects, 
                          day=day,
                          start_time=request.args.get('start_time', ''),
                          end_time=request.args.get('end_time', ''),
                          subject_id=request.args.get('subject_id', ''),
                          task_description=request.args.get('task_description', ''),
                          error_message=request.args.get('error_message', ''),
                          app_mode='trackademic')

@app.route('/trackademic/add_timetable', methods=['POST'])
def add_timetable():
    """Add a subject to the timetable database"""
    if 'user_id' not in session:  # Only check if user is logged in
        return redirect('/login')
    
    user_id = session['user_id']
    day = int(request.form.get('day', 0))
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    subject_id = request.form.get('subject_id', '')
    custom_task = request.form.get('custom_task', '').strip()
    task_description = request.form.get('task_description', '').strip()
    
    if not start_time or not end_time:
        error_message = "Both start and end times are required!"
        conn = get_db_connection()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
        conn.close()
        
        return render_template('add_subject.html', 
                              subjects=subjects, 
                              day=day,
                              error_message=error_message,
                              start_time=start_time,
                              end_time=end_time,
                              subject_id=subject_id,
                              custom_task=custom_task,
                              task_description=task_description,
                              app_mode='trackademic')
    
    # Validate that end time is not earlier than start time
    if not is_valid_time_range(start_time, end_time):
        error_message = f"End time ({end_time}) cannot be earlier than or equal to start time ({start_time})."
        conn = get_db_connection()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
        conn.close()
        
        return render_template('add_subject.html', 
                              subjects=subjects, 
                              day=day,
                              error_message=error_message,
                              start_time=start_time,
                              end_time=end_time,
                              subject_id=subject_id,
                              custom_task=custom_task,
                              task_description=task_description,
                              app_mode='trackademic')
    
    # Handle custom task
    if subject_id == 'custom':
        if not custom_task:
            error_message = "Please enter a task name for the custom task."
            conn = get_db_connection()
            subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
            conn.close()
            
            return render_template('add_subject.html', 
                                  subjects=subjects, 
                                  day=day,
                                  error_message=error_message,
                                  start_time=start_time,
                                  end_time=end_time,
                                  subject_id=subject_id,
                                  custom_task=custom_task,
                                  task_description=task_description,
                                  app_mode='trackademic')
        
        # Create a temporary subject for the custom task
        conn = get_db_connection()
        try:
            timestamp = int(time.time())
            custom_code = f"CUSTOM_{timestamp}"
            
            conn.execute(
                'INSERT INTO subjects (subject_name, subject_code) VALUES (?, ?)',
                (custom_task, custom_code)
            )
            conn.commit()
            
            # Get the new subject_id
            new_subject = conn.execute(
                'SELECT subject_id FROM subjects WHERE subject_code = ?',
                (custom_code,)
            ).fetchone()
            
            subject_id = new_subject['subject_id']
        except Exception as e:
            conn.close()
            error_message = f"Error creating custom task: {str(e)}"
            conn = get_db_connection()
            subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
            conn.close()
            
            return render_template('add_subject.html', 
                                  subjects=subjects, 
                                  day=day,
                                  error_message=error_message,
                                  start_time=start_time,
                                  end_time=end_time,
                                  subject_id=subject_id,
                                  custom_task=custom_task,
                                  task_description=task_description,
                                  app_mode='trackademic')
    else:
        subject_id = int(subject_id)
        conn = get_db_connection()  # Get connection for regular subjects
    
    # Combine start and end time into a single time slot string
    time_slot = f"{start_time} - {end_time}"
    
    try:
        # Check if time slot is already taken
        existing = conn.execute(
            'SELECT * FROM timetable WHERE day = ? AND time_slot = ?',
            (day, time_slot)
        ).fetchone()
        
        if existing:
            conn.close()
            error_message = f"This time slot ({time_slot}) is already taken!"
            
            conn = get_db_connection()
            subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
            conn.close()
            
            return render_template('add_subject.html', 
                                  subjects=subjects, 
                                  day=day,
                                  error_message=error_message,
                                  start_time=start_time,
                                  end_time=end_time,
                                  subject_id=subject_id,
                                  custom_task=custom_task,
                                  task_description=task_description,
                                  app_mode='trackademic')
        
        # Insert into timetable WITH task_description
        conn.execute(
            'INSERT INTO timetable (subject_id, user_id, day, time_slot, task_description) VALUES (?, ?, ?, ?, ?)',
            (subject_id, user_id, day, time_slot, task_description)
    )
        conn.commit()
        conn.close()
        
        return redirect('/trackademic/edit_timetable')
    
    except Exception as e:
        error_message = f"Error adding to timetable: {str(e)}"
        conn = get_db_connection()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
        conn.close()
        
        return render_template('add_subject.html', 
                              subjects=subjects, 
                              day=day,
                              error_message=error_message,
                              start_time=start_time,
                              end_time=end_time,
                              subject_id=subject_id,
                              custom_task=custom_task,
                              task_description=task_description,
                              app_mode='trackademic')
    
@app.route('/trackademic/edit_timetable')
def edit_timetable():
    """Enter edit mode - accessible to all logged-in users"""
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    conn = get_db_connection()
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
    
    timetable_data = conn.execute('''
        SELECT t.*, s.subject_name, s.subject_code, t.task_description
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        WHERE t.user_id = ?
        ORDER BY t.day, t.time_slot
    ''', (user_id,)).fetchall()
    
    schedule = {}
    for item in timetable_data:
        day = item['day']
        time_slot = item['time_slot']
        if day not in schedule:
            schedule[day] = {}
        schedule[day][time_slot] = {
            'subject_name': item['subject_name'],
            'subject_code': item['subject_code'],
            'time_slot': time_slot,
            'task_description': item['task_description'],
            'subject_id': item['subject_id'],
            'timetable_id': item['timetable_id']
        }
    
    # Get today's schedule
    today_schedule = get_today_schedule(user_id)
    
    # Get weekly summary
    weekly_summary = get_weekly_summary(user_id)
    
    conn.close()

    return render_template('timetable.html', subjects=subjects, schedule=schedule, 
                          edit_mode=True, today_schedule=today_schedule, 
                          weekly_summary=weekly_summary, app_mode='trackademic')

def is_valid_time_range(start_time_str, end_time_str):
    """Helper function to validate if end time is after start time"""
    def time_to_minutes(time_str):
        try:
            time_str = time_str.strip().upper()
            
            # Check if AM/PM is present
            if " AM" in time_str:
                time_part = time_str.replace(" AM", "")
                is_pm = False
            elif " PM" in time_str:
                time_part = time_str.replace(" PM", "")
                is_pm = True
            else:
                # Default to AM if no indicator
                time_part = time_str
                is_pm = False
            
            # Handle case where time might have trailing spaces
            time_part = time_part.strip()
            
            if ":" in time_part:
                hours_str, minutes_str = time_part.split(":")
                hours = int(hours_str)
                minutes = int(minutes_str)
            else:
                hours = int(time_part)
                minutes = 0
            
            # Convert 12-hour to 24-hour format
            if is_pm:
                if hours != 12:
                    hours += 12
            else:
                if hours == 12:
                    hours = 0
            
            return hours * 60 + minutes
        except Exception as e:
            print(f"Error parsing time '{time_str}': {e}")
            return -1  # Invalid time
    
    try:
        start_minutes = time_to_minutes(start_time_str)
        end_minutes = time_to_minutes(end_time_str)
        
        if start_minutes == -1 or end_minutes == -1:
            return False
            
        return end_minutes > start_minutes
    except Exception as e:
        print(f"Time validation error: {e}")
        return False

@app.route('/trackademic/remove_timetable', methods=['POST'])
def remove_timetable():
    """Remove a subject from timetable database - user can only remove their own"""
    if 'user_id' not in session:
        return redirect('/trackademic/timetable')
    
    user_id = session['user_id']
    day = int(request.form.get('day', 0))
    time = request.form.get('time', '')
    
    try:
        conn = get_db_connection()
        conn.execute(
            'DELETE FROM timetable WHERE user_id = ? AND day = ? AND time_slot = ?',
            (user_id, day, time)
        )
        conn.commit()
        conn.close()
        
        return redirect('/trackademic/edit_timetable')
    
    except Exception as e:
        return f'<h1>Error removing from timetable: {str(e)}</h1><p><a href="/trackademic/edit_timetable">Go back</a></p>'

@app.route('/trackademic/clear_timetable', methods=['POST'])
def clear_timetable():
    """Clear all timetable data for the current user"""
    if 'user_id' not in session:
        return redirect('/trackademic/timetable')
    
    user_id = session['user_id']
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM timetable WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return redirect('/trackademic/edit_timetable')
    
    except Exception as e:
        return f'<h1>Error clearing timetable: {str(e)}</h1><p><a href="/trackademic/edit_timetable">Go back</a></p>'
    
@app.route('/trackademic/complete_task', methods=['POST'])
def complete_task():
    """Mark a task as completed and remove it from timetable"""
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    try:
        day = int(request.form.get('day', 0))
        time_slot = request.form.get('time_slot', '')
        subject_id = request.form.get('subject_id', '')
        
        conn = get_db_connection()
        
        # First, check if this is a custom task (subject_code starts with CUSTOM_)
        # AND belongs to the current user
        subject = conn.execute('''
            SELECT s.subject_code 
            FROM subjects s 
            JOIN timetable t ON s.subject_id = t.subject_id
            WHERE s.subject_id = ? AND t.user_id = ?
        ''', (subject_id, user_id)).fetchone()
        
        if subject and subject['subject_code'].startswith('CUSTOM_'):
            # Delete the custom subject from subjects table
            # Only if no other user is using it
            other_users = conn.execute(
                'SELECT COUNT(*) FROM timetable WHERE subject_id = ? AND user_id != ?',
                (subject_id, user_id)
            ).fetchone()[0]
            
            if other_users == 0:
                conn.execute(
                    'DELETE FROM subjects WHERE subject_id = ?',
                    (subject_id,)
                )
        
        # Delete from timetable - only user's own entry
        conn.execute(
            'DELETE FROM timetable WHERE user_id = ? AND day = ? AND time_slot = ?',
            (user_id, day, time_slot)
        )
        
        conn.commit()
        conn.close()
        
        return redirect('/trackademic/timetable')
    
    except Exception as e:
        return f'<h1>Error completing task: {str(e)}</h1><p><a href="/trackademic/timetable">Go back</a></p>'

# ============ HELPER FUNCTIONS FOR TRACKADEMIC ============
def get_today_schedule(user_id):
    """Get today's schedule based on current day of week for specific user"""
    today = datetime.datetime.today().weekday()
    
    conn = get_db_connection()
    today_schedule = conn.execute('''
        SELECT t.time_slot, s.subject_name, s.subject_code, t.task_description, s.subject_id
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        WHERE t.user_id = ? AND t.day = ?
        ORDER BY t.time_slot
    ''', (user_id, today)).fetchall()
    
    conn.close()
    return today_schedule

def get_weekly_summary(user_id):
    """Get summary of all scheduled tasks for the week for specific user"""
    conn = get_db_connection()
    
    weekly_summary = conn.execute('''
        SELECT 
            t.day,
            t.time_slot,
            s.subject_name,
            s.subject_code,
            s.subject_id,
            t.task_description,
            COUNT(*) as task_count
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        WHERE t.user_id = ?
        GROUP BY t.day, s.subject_name, t.time_slot
        ORDER BY t.day, t.time_slot
    ''', (user_id,)).fetchall()
    
    conn.close()
    return weekly_summary

# ============ SOCIAL APP ROUTES ============
@app.route('/social/dashboard', methods=['GET', 'POST'])
def social_dashboard():
    """Social platform dashboard"""
    if "user_id" not in session:
        return redirect("/login")
    
    session['app_mode'] = 'social'
    
    user_id = session["user_id"]
    username = session["username"]
    search_query = request.args.get('search', '')

    if request.method == "POST":
        content = request.form.get("content")
        file = request.files.get("file")
        filename = None
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_social_db_connection()
        db.execute("INSERT INTO posts (user_id, content, filename) VALUES (?, ?, ?)", (user_id, content, filename))
        db.commit()
        db.close()
        return redirect("/social/dashboard")

    db = get_social_db_connection()
    
    # Get folders
    cursor = db.execute("""
        SELECT DISTINCT folders.id, folders.folder_name 
        FROM folders 
        JOIN saved_posts ON folders.id = saved_posts.folder_id 
        WHERE folders.user_id=?
    """, (user_id,))
    folders = cursor.fetchall()

    # Get posts
    query = """
        SELECT 
            posts.id, posts.content, posts.filename, users.username, posts.user_id,
            EXISTS(SELECT 1 FROM saved_posts WHERE post_id = posts.id AND user_id = ?) as is_saved
        FROM posts 
        JOIN users ON posts.user_id = users.id
    """
    params = [user_id]
    if search_query:
        query += " WHERE posts.content LIKE ? OR users.username LIKE ?"
        params.append(f'%{search_query}%')
        params.append(f'%{search_query}%')

    query += " ORDER BY posts.id DESC"
    cursor = db.execute(query, params)
    posts = cursor.fetchall()
    
    # Get comments for each post
    posts_with_comments = []
    for post in posts:
        cursor = db.execute(
            "SELECT id, username, comment, user_id FROM comments WHERE post_id=? ORDER BY created_at ASC",
            (post[0],)
        )
        comments = cursor.fetchall()
        posts_with_comments.append((*post, comments))

    db.close()
    
    return render_template("dashboard.html", 
                         username=username, 
                         posts=posts_with_comments, 
                         folders=folders, 
                         search_query=search_query,
                         app_mode='social')

@app.route("/social/save_post/<int:post_id>", methods=["POST"])
def save_post(post_id):
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    folder_id = request.form.get("folder_id")
    new_folder_name = request.form.get("new_folder_name")

    db = get_social_db_connection()
    if new_folder_name and new_folder_name.strip():
        cursor = db.execute("INSERT INTO folders (user_id, folder_name) VALUES (?, ?)", 
                            (user_id, new_folder_name.strip()))
        folder_id = cursor.lastrowid
    
    if folder_id:
        db.execute("INSERT INTO saved_posts (user_id, post_id, folder_id) VALUES (?, ?, ?)", 
                   (user_id, post_id, folder_id))
        db.commit()
    db.close()
    return redirect("/social/dashboard")

@app.route("/social/saved")
def saved_posts():
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    search_query = request.args.get('search', '')
    db = get_social_db_connection()
    query = """
        SELECT f.folder_name, p.content, p.filename, u.username, sp.id
        FROM saved_posts sp
        JOIN folders f ON sp.folder_id = f.id
        JOIN posts p ON sp.post_id = p.id
        JOIN users u ON p.user_id = u.id
        WHERE sp.user_id = ?
    """
    params = [user_id]
    if search_query:
        query += " AND (p.content LIKE ? OR f.folder_name LIKE ?)"
        params.append(f'%{search_query}%')
        params.append(f'%{search_query}%')

    cursor = db.execute(query, params)
    data = cursor.fetchall()
    organized = {}
    for folder, content, file, poster, sp_id in data:
        if folder not in organized: organized[folder] = []
        organized[folder].append({'content': content, 'file': file, 'poster': poster, 'sp_id': sp_id})
    db.close()
    return render_template("saved.html", organized=organized, username=session["username"], search_query=search_query, app_mode='social')

@app.route("/social/unsave/<int:sp_id>", methods=["POST"])
def unsave(sp_id):
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    db = get_social_db_connection()
    
    # Check if folder becomes empty after deletion
    cursor = db.execute("SELECT folder_id FROM saved_posts WHERE id=? AND user_id=?", (sp_id, user_id))
    result = cursor.fetchone()
    
    if result:
        folder_id = result[0]
        db.execute("DELETE FROM saved_posts WHERE id=? AND user_id=?", (sp_id, user_id))
        
        # Check if any posts are still in this folder
        check = db.execute("SELECT COUNT(*) FROM saved_posts WHERE folder_id=?", (folder_id,)).fetchone()
        if check[0] == 0:
            # Delete the folder if it's empty
            db.execute("DELETE FROM folders WHERE id=?", (folder_id,))
            
    db.commit()
    db.close()
    return redirect("/social/saved")

@app.route("/social/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    db = get_social_db_connection()
    cursor = db.execute("SELECT filename FROM posts WHERE id=? AND user_id=?", (post_id, user_id))
    result = cursor.fetchone()
    if result:
        filename = result[0]
        if filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(path): os.remove(path)
        db.execute("DELETE FROM posts WHERE id=? AND user_id=?", (post_id, user_id))
        db.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        db.execute("DELETE FROM saved_posts WHERE post_id=?", (post_id,))
    db.commit()
    db.close()
    return redirect("/social/dashboard")

@app.route("/social/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    if "user_id" not in session: return redirect("/login")
    comment_text = request.form.get("comment")
    if comment_text:
        db = get_social_db_connection()
        db.execute("INSERT INTO comments (post_id, user_id, username, comment) VALUES (?, ?, ?, ?)",
                   (post_id, session["user_id"], session["username"], comment_text))
        db.commit()
        db.close()
    return redirect("/social/dashboard")

@app.route("/social/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    if "user_id" not in session: return redirect("/login")
    db = get_social_db_connection()
    cursor = db.execute("SELECT user_id FROM comments WHERE id=?", (comment_id,))
    result = cursor.fetchone()
    if result and result[0] == session["user_id"]:
        db.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        db.commit()
    db.close()
    return redirect("/social/dashboard")

@app.route('/debug/gpa-data')
def debug_gpa_data():
    """Debug endpoint to check all GPA data in database"""
    if 'is_admin' not in session or session['is_admin'] != 1:
        return "Admin access required", 403
    
    conn = get_db_connection()
    all_gpa = conn.execute('''
        SELECT g.*, u.username, u.email 
        FROM gpa g 
        LEFT JOIN trackademic_users u ON g.user_id = u.user_id
        ORDER BY g.user_id, g.trimester
    ''').fetchall()
    
    html = '<h1>All GPA Data in Database</h1>'
    html += f'<p>Total records: {len(all_gpa)}</p>'
    html += '<table border="1">'
    html += '<tr><th>ID</th><th>User ID</th><th>Username</th><th>Email</th><th>Trimester</th><th>GPA</th><th>Credits</th><th>Created</th></tr>'
    
    for gpa in all_gpa:
        html += f'<tr>'
        html += f'<td>{gpa["gpa_id"]}</td>'
        html += f'<td>{gpa["user_id"]}</td>'
        html += f'<td>{gpa["username"] or "N/A"}</td>'
        html += f'<td>{gpa["email"] or "N/A"}</td>'
        html += f'<td>{gpa["trimester"]}</td>'
        html += f'<td>{gpa["gpa"]:.2f}</td>'
        html += f'<td>{gpa["total_credits"]}</td>'
        html += f'<td>{gpa["created_at"]}</td>'
        html += f'</tr>'
    
    html += '</table>'
    html += '<p><a href="/admin/home">Back to Admin</a></p>'
    
    conn.close()
    return html

@app.route('/debug/user-gpa')
def debug_user_gpa():
    """Debug endpoint to check GPA data for current user"""
    if 'user_id' not in session:
        return "Not authenticated", 401
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    # Get current user's GPA data
    user_gpa = conn.execute('''
        SELECT g.*, u.username 
        FROM gpa g 
        JOIN trackademic_users u ON g.user_id = u.user_id
        WHERE g.user_id = ?
        ORDER BY g.trimester
    ''', (user_id,)).fetchall()
    
    # Get all GPA data for comparison
    all_gpa = conn.execute('''
        SELECT g.*, u.username 
        FROM gpa g 
        JOIN trackademic_users u ON g.user_id = u.user_id
        ORDER BY g.user_id, g.trimester
    ''').fetchall()
    
    conn.close()
    
    html = f'<h1>GPA Data for User ID: {user_id}</h1>'
    
    html += '<h2>Your GPA Data:</h2>'
    if user_gpa:
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>User ID</th><th>Username</th><th>Trimester</th><th>GPA</th><th>Credits</th></tr>'
        for gpa in user_gpa:
            html += f'<tr>'
            html += f'<td>{gpa["gpa_id"]}</td>'
            html += f'<td>{gpa["user_id"]}</td>'
            html += f'<td>{gpa["username"]}</td>'
            html += f'<td>{gpa["trimester"]}</td>'
            html += f'<td>{gpa["gpa"]:.2f}</td>'
            html += f'<td>{gpa["total_credits"]}</td>'
            html += f'</tr>'
        html += '</table>'
    else:
        html += '<p>No GPA data found for your account.</p>'
    
    html += '<h2>All GPA Data in Database (for comparison):</h2>'
    html += f'<p>Total records: {len(all_gpa)}</p>'
    html += '<table border="1">'
    html += '<tr><th>ID</th><th>User ID</th><th>Username</th><th>Trimester</th><th>GPA</th><th>Credits</th></tr>'
    
    for gpa in all_gpa:
        html += f'<tr>'
        html += f'<td>{gpa["gpa_id"]}</td>'
        html += f'<td>{gpa["user_id"]}</td>'
        html += f'<td>{gpa["username"]}</td>'
        html += f'<td>{gpa["trimester"]}</td>'
        html += f'<td>{gpa["gpa"]:.2f}</td>'
        html += f'<td>{gpa["total_credits"]}</td>'
        html += f'</tr>'
    
    html += '</table>'
    html += '<p><a href="/trackademic/calculator">Back to Calculator</a></p>'
    
    return html

if __name__ == '__main__':
    app.run(debug=True, port=5000)