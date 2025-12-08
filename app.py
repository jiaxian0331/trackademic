from flask import Flask, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

def get_db_connection():
    try:
        conn = sqlite3.connect('trackademic.db')
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    """Create tables if they don't exist"""
    conn = sqlite3.connect('trackademic.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL UNIQUE,
        subject_code TEXT UNIQUE,
        credit_hours INTEGER DEFAULT 3
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_data (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS gpa (
        trimester_id INTEGER PRIMARY KEY AUTOINCREMENT,
        trimester TEXT NOT NULL UNIQUE,
        gpa REAL NOT NULL CHECK (gpa >= 0.0 AND gpa <= 4.0)
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

init_database()

@app.route('/')
def home():
    return '''
    <h1>Trackademic Database</h1>
    
    <h2>View Data:</h2>
    <ul>
        <li><a href="/subjects">View All Subjects</a></li>
        <li><a href="/user">View All Users</a></li>
<<<<<<< HEAD
        <li><a href="/gpa">View GPA Data</a></li>
        <li><a href="/create-subjects-db">Reset Subjects Database</a></li>
        <li><a href="/create-user-db">Reset User Database</a></li>
        <li><a href="/create-notes-db">Reset Notes Database</a></li>
        <li><a href="/create-gpa-db">Reset GPA Database</a></li>
=======
        <li><a href="/notes">View All Notes</a></li>
        <li><a href="/gpa">View GPA Data</a></li>
    </ul>
    
    <h2>Reset Tables:</h2>
    <ul>
        <li><a href="/reset-subjects" onclick="return confirm('Reset Subjects table?')">Reset Subjects</a></li>
        <li><a href="/reset-users" onclick="return confirm('Reset Users table?')">Reset Users</a></li>
        <li><a href="/reset-notes" onclick="return confirm('Reset Notes table?')">Reset Notes</a></li>
        <li><a href="/reset-gpa" onclick="return confirm('Reset GPA table?')">Reset GPA</a></li>
>>>>>>> jiaxian
    </ul>
    '''

@app.route('/subjects')
def list_subjects():
    try:
        conn = get_db_connection()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
        conn.close()
        
        if not subjects:
            return '<h1>No subjects found.</h1><p><a href="/reset-subjects">Reset subjects database</a></p>'
        
        html = '<h1>All Subjects</h1>'
        html += '<p><a href="/add-subject" >+ Add New Subject</a></p>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>Code</th><th>Subject Name</th><th>Credit Hours</th><th>Actions</th></tr>'
        
        for subject in subjects:
            html += f'<tr>'
            html += f'<td>{subject["subject_id"]}</td>'
            html += f'<td>{subject["subject_code"]}</td>'
            html += f'<td>{subject["subject_name"]}</td>'
            html += f'<td>{subject["credit_hours"]}</td>'
            html += f'<td>'
            html += f'<a href="/edit-subject/{subject["subject_id"]}" style="border-radius: 3px; margin: 0 5px;">Edit</a>'
            html += f'<a href="/delete-subject/{subject["subject_id"]}" style="border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this subject?\')">Delete</a>'
            html += f'</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/">Back to Home</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error accessing database: {str(e)}</h1>'

@app.route('/add-subject', methods=['GET', 'POST'])
def add_subject():
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
            return redirect('/subjects')
        except Exception as e:
            return f'<h1>Failed to add subject: Subject already existed.</h1><p><a href="/add-subject">Try again</a></p>'
    
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
            <a href="/subjects" style="background: #ccc; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Cancel</a>
        </div>
    </form>
    '''

@app.route('/edit-subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
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
            return redirect('/subjects')
        except Exception as e:
            conn.close()
            return f'<h1>Error updating subject!</h1><p><a href="/edit-subject/{subject_id}">Try again</a></p>'
    
    subject = conn.execute('SELECT * FROM subjects WHERE subject_id = ?', (subject_id,)).fetchone()
    conn.close()
    
    if not subject:
        return '<h1>Subject not found</h1><p><a href="/subjects">Back to subjects</a></p>'
    
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
            <a href="/subjects" style="background: #ccc; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Cancel</a>
        </div>
    </form>
    '''

@app.route('/delete-subject/<int:subject_id>')
def delete_subject(subject_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM subjects WHERE subject_id = ?', (subject_id,))
        conn.commit()
        conn.close()
        return f'<h1>Subject deleted successfully!</h1><p><a href="/subjects">Back to subjects</a></p>'
    except Exception as e:
        return f'<h1>Error deleting subject!</h1><p><a href="/subjects">Back to subjects</a></p>'
    
@app.route('/user')
def list_user():
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user_data ORDER BY user_id').fetchall()
        conn.close()
        
        if not user:
            return '<h1>No user found.</h1><p><a href="/reset-users">Reset users database</a></p>'
        
        html = '<h1>All Users</h1>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>Username</th><th>Email</th><th>Password</th><th>Actions</th></tr>'
        
        for users in user:
            html += f'<tr>'
            html += f'<td>{users["user_id"]}</td>'
            html += f'<td>{users["username"]}</td>'
            html += f'<td>{users["email"]}</td>'
            html += f'<td>{users["password"]}</td>'
            html += f'<td>'
            html += f'<a href="/delete-user/{users["user_id"]}" style="border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this user?\')">Delete</a>'
            html += f'</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/">Back to Home</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error accessing database: {str(e)}</h1>'
    
@app.route('/delete-user/<int:user_id>')
def delete_user(user_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM user_data WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        return f'<h1>User deleted successfully!</h1><p><a href="/user">Back to users</a></p>'
    except Exception as e:
        return f'<h1>Error deleting user! {str(e)}</h1><p><a href="/user">Back to users</a></p>'
<<<<<<< HEAD
    
@app.route('/gpa')
def list_gpa():
    try:
        conn = get_db_connection()
        gpa = conn.execute('SELECT * FROM gpa ORDER BY trimester_id').fetchall()
        conn.close()
        
        if not gpa:
            return '<h1>No GPA found.</h1><p><a href="/create-gpa-db">Create database first</a></p>'
        
        html = '<h1>GPA Data</h1>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>Trimester</th><th>GPA</th><th>Actions</th></tr>'
        
        for cgpa in gpa:
            html += f'<tr>'
            html += f'<td>{cgpa["trimester_id"]}</td>'
            html += f'<td>{cgpa["Trimester"]}</td>'
            html += f'<td>{cgpa["GPA"]}</td>'
            html += f'<td>'
            html += f'<a href="/delete-gpa/{cgpa["trimester_id"]}" style="border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this GPA data?\')">Delete</a>'
            html += f'</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/">Back to Home</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error accessing database: {str(e)}</h1>'
    
@app.route('/delete-gpa/<int:trimester_id>')
def delete_gpa(trimester_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM gpa WHERE trimester_id = ?', (trimester_id,))
        conn.commit()
        conn.close()
        return f'<h1>GPA deleted successfully!</h1><p><a href="/gpa">Back to GPA Data</a></p>'
    except Exception as e:
        return f'<h1>Error deleting GPA! {str(e)}</h1><p><a href="/gpa">Back to GPA Data</a></p>'

@app.route('/create-subjects-db')
def create_subjects_database_route():
    try:
        import Databases.subjects
        Databases.subjects.create_subjects_database()
        return '''
        <h1>Database created successfully!</h1>
        <p><a href="/subjects">View Subjects</a></p>
        <p><a href="/">Back to Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating database! {str(e)}</h1>'
=======
>>>>>>> jiaxian
    
@app.route('/gpa')
def list_gpa():
    try:
        conn = get_db_connection()
        gpa = conn.execute('SELECT * FROM gpa ORDER BY trimester_id').fetchall()
        conn.close()
        
        if not gpa:
            return '<h1>No GPA data found.</h1><p><a href="/reset-gpa">Reset GPA database</a></p>'
        
        html = '<h1>All GPA Data</h1>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>Trimester</th><th>GPA</th><th>Actions</th></tr>'
        
        for cgpa in gpa:
            html += f'<tr>'
            html += f'<td>{cgpa["trimester_id"]}</td>'
            html += f'<td>{cgpa["trimester"]}</td>'
            html += f'<td>{cgpa["gpa"]}</td>'
            html += f'<td>'
            html += f'<a href="/delete-gpa/{cgpa["trimester_id"]}" style="border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this GPA data?\')">Delete</a>'
            html += f'</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/">Back to Home</a></p>'
        return html
    except Exception as e:
<<<<<<< HEAD
        return f'<h1>Error creating database! {str(e)}</h1>'
    
@app.route('/create-notes-db')
def create_notes_database_route():
    try:
        import Databases.notes
        Databases.notes.create_notes_database()
        return '''
        <h1>Database reset successfully!</h1>
        <p><a href="/">Back to Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating database! {str(e)}</h1>'
    
@app.route('/create-gpa-db')
def create_gpa_database_route():
    try:
        import Databases.gpa
        Databases.gpa.create_gpa_database()
        return '''
        <h1>Database reset successfully!</h1>
        <p><a href="/">Back to Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating database! {str(e)}</h1>'
=======
        return f'<h1>Error accessing database!</h1>'

@app.route('/delete-gpa/<int:trimester_id>')
def delete_gpa(trimester_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM gpa WHERE trimester_id = ?', (trimester_id,))
        conn.commit()
        conn.close()
        return f'<h1>GPA data deleted successfully!</h1><p><a href="/gpa">Back to GPA Data</a></p>'
    except Exception as e:
        return f'<h1>Error deleting GPA data!</h1><p><a href="/gpa">Back to GPA Data</a></p>'
    
@app.route('/notes')
def list_notes():
    try:
        conn = get_db_connection()
        notes = conn.execute('''
            SELECT n.note_id, n.subject_id, n.user_id, n.file_name, n.file, 
                   s.subject_code, s.subject_name
            FROM notes n
            LEFT JOIN subjects s ON n.subject_id = s.subject_id
            ORDER BY n.note_id
        ''').fetchall()
        conn.close()
        
        if not notes:
            return '<h1>No notes found.</h1><p><a href="/reset-notes">Reset notes database</a></p>'
        
        html = '<h1>All Notes</h1>'
        html += '<table border="1">'
        html += '<tr><th>ID</th><th>Subject ID</th><th>Subject Code</th><th>Subject Name</th><th>User ID</th><th>File Name</th><th>File</th></tr>'
        
        for note in notes:
            html += f'<tr>'
            html += f'<td>{note["note_id"]}</td>'
            html += f'<td>{note["subject_id"]}</td>'
            html += f'<td>{note["subject_code"] if note["subject_code"] else "N/A"}</td>'
            html += f'<td>{note["subject_name"] if note["subject_name"] else "N/A"}</td>'
            html += f'<td>{note["user_id"]}</td>'
            html += f'<td>{note["file_name"]}</td>'
            html += f'<td>{"File attached" if note["file"] else "No file"}</td>'
            html += f'</tr>'
        
        html += '</table>'
        html += '<p><a href="/">Back to Home</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error accessing database: {str(e)}</h1>'
    
@app.route('/reset-subjects')
def reset_subjects():
    """Reset only the subjects table"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute('DELETE FROM subjects')
        
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
        return '<h1>Subjects table reset successfully!</h1><p><a href="/subjects">View Subjects</a> | <a href="/">Home</a></p>'
    
    except Exception as e:
        if conn:
            conn.rollback()
        return f'<h1>Error resetting subjects: {str(e)}</h1>'
    
    finally:
        if conn:
            conn.close()

@app.route('/reset-users')
def reset_users():
    """Reset only the users table"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_data')
        
        user_data = [
            ('jiaxian0331', 'hoejiaxian@gmail.com', 'jiaxian0000'),
        ]
        
        cursor.executemany(
            'INSERT INTO user_data (username, email, password) VALUES (?, ?, ?)',
            user_data
        )
        
        conn.commit()
        return '<h1>Users table reset successfully!</h1><p><a href="/user">View Users</a> | <a href="/">Home</a></p>'
    
    except Exception as e:
        if conn:
            conn.rollback()
        return f'<h1>Error resetting users: {str(e)}</h1>'
    
    finally:
        if conn:
            conn.close()

@app.route('/reset-notes')
def reset_notes():
    """Reset only the notes table"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute('DELETE FROM notes')
        
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
        return '<h1>Notes table reset successfully!</h1><p><a href="/notes">View Notes</a> | <a href="/">Home</a></p>'
    
    except Exception as e:
        if conn:
            conn.rollback()
        return f'<h1>Error resetting notes: {str(e)}</h1>'
    
    finally:
        if conn:
            conn.close()

@app.route('/reset-gpa')
def reset_gpa():
    """Reset only the GPA table"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM gpa')
        
        gpa = [
            ('Trimester 2510', 3.73),
        ]
        
        cursor.executemany(
            'INSERT INTO gpa (trimester, gpa) VALUES (?, ?)',
            gpa
        )
        
        conn.commit()
        return '<h1>GPA table reset successfully!</h1><p><a href="/gpa">View GPA</a> | <a href="/">Home</a></p>'
    
    except Exception as e:
        if conn:
            conn.rollback()
        return f'<h1>Error resetting GPA: {str(e)}</h1>'
    
    finally:
        if conn:
            conn.close()
>>>>>>> jiaxian

if __name__ == '__main__':
    app.run(debug=True)
