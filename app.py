from flask import Flask, request, redirect, url_for, render_template, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for sessions

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
    CREATE TABLE IF NOT EXISTS timetable (
        timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        day INTEGER NOT NULL,
        time_slot TEXT NOT NULL,
        task_description TEXT DEFAULT '',
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
        UNIQUE(day, time_slot)
    )
    ''')

    try:
        cursor.execute("ALTER TABLE subjects ADD COLUMN task_description TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    
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
    
    try:
        cursor.execute("ALTER TABLE timetable ADD COLUMN task_description TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        # Column already exists, ignore the error
        pass

    conn.commit()
    conn.close()

init_database()

@app.route('/')
def home():
    return '''
    <h1>Trackademic Database</h1>

    <h2>Application:</h2>
    <ul>
        <li><a href="/timetable">Go to Timetable</a></li>
    </ul>
    
    <h2>View Data:</h2>
    <ul>
        <li><a href="/subjects">View All Subjects</a></li>
        <li><a href="/user">View All Users</a></li>
        <li><a href="/gpa">View GPA Data</a></li>
    </ul>

    <h2>Reset Data:</h2>
    <ul>
        <li><a href="/create-subjects-db">Reset Subjects Database</a></li>
        <li><a href="/create-user-db">Reset User Database</a></li>
        <li><a href="/create-notes-db">Reset Notes Database</a></li>
        <li><a href="/create-gpa-db">Reset GPA Database</a></li>
    </ul>
    '''

def get_today_schedule():
    """Get today's schedule based on current day of week"""
    import datetime
    
    today = datetime.datetime.today().weekday()
    
    conn = get_db_connection()
    today_schedule = conn.execute('''
        SELECT t.time_slot, s.subject_name, s.subject_code, t.task_description
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        WHERE t.day = ?
        ORDER BY t.time_slot
    ''', (today,)).fetchall()
    
    conn.close()
    return today_schedule

def get_weekly_summary():
    """Get summary of all scheduled tasks for the week"""
    conn = get_db_connection()
    
    weekly_summary = conn.execute('''
        SELECT 
            t.day,
            t.time_slot,
            s.subject_name,
            s.subject_code,
            t.task_description,
            COUNT(*) as task_count
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        GROUP BY t.day, s.subject_name
        ORDER BY t.day, t.time_slot
    ''').fetchall()
    
    conn.close()
    return weekly_summary

@app.route('/subjects')
def list_subjects():
    try:
        conn = get_db_connection()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
        conn.close()
        
        if not subjects:
            return '<h1>No subjects found.</h1><p><a href="/reset-subjects">Reset subjects database</a></p>'
        
        html = '<h1>All Subjects</h1>'
        html += '<p><a href="/add-subject-form-db">+ Add New Subject</a></p>'
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

@app.route('/add-subject-form-db', methods=['GET', 'POST'])
def add_subject_form_db():
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
            return f'<h1>Failed to add subject: {str(e)}</h1><p><a href="/add-subject-form-db">Try again</a></p>'
    
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
    
@app.route('/create-user-db')
def create_user_database_route():
    try:
        import Databases.user_data
        Databases.user_data.create_user_database()
        return '''
        <h1>User database reset successfully!</h1>
        <p><a href="/user">View Users</a></p>
        <p><a href="/">Back to Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error creating user database! {str(e)}</h1>'

@app.route('/timetable')
def timetable():
    """View timetable in non-edit mode"""
    conn = get_db_connection()
    timetable_data = conn.execute('''
        SELECT t.*, s.subject_name, s.subject_code, t.task_description
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        ORDER BY t.day, t.time_slot
    ''').fetchall()
    
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
            'task_description': item['task_description']  # ADD THIS
        }
    
    # Get today's schedule
    today_schedule = get_today_schedule()
    
    # Get weekly summary
    weekly_summary = get_weekly_summary()
    
    conn.close()
    
    return render_template('timetable.html', schedule=schedule, edit_mode=False, 
                          today_schedule=today_schedule, weekly_summary=weekly_summary)

@app.route('/edit_timetable')
def edit_timetable():
    """Enter edit mode"""
    conn = get_db_connection()
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
    
    timetable_data = conn.execute('''
        SELECT t.*, s.subject_name, s.subject_code, t.task_description
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.subject_id
        ORDER BY t.day, t.time_slot
    ''').fetchall()
    
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
            'task_description': item['task_description']  # ADD THIS
        }
    
    # Get today's schedule
    today_schedule = get_today_schedule()
    
    # Get weekly summary
    weekly_summary = get_weekly_summary()
    
    conn.close()

    return render_template('timetable.html', subjects=subjects, schedule=schedule, 
                          edit_mode=True, today_schedule=today_schedule, 
                          weekly_summary=weekly_summary)

@app.route('/add_subject_form')
def add_subject_form():
    """Show form to add a subject to timetable"""
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
                          error_message=request.args.get('error_message', ''))

@app.route('/add_timetable', methods=['POST'])
def add_timetable():
    """Add a subject to the timetable database"""
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
                              task_description=task_description)
    
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
                              task_description=task_description)
    
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
                                  task_description=task_description)
        
        # Create a temporary subject for the custom task
        conn = get_db_connection()
        try:
            import time
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
                                  task_description=task_description)
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
                                  task_description=task_description)
        
        # Insert into timetable WITH task_description
        conn.execute(
            'INSERT INTO timetable (subject_id, day, time_slot, task_description) VALUES (?, ?, ?, ?)',
            (subject_id, day, time_slot, task_description)  # Add task_description here
        )
        conn.commit()
        conn.close()
        
        return redirect('/edit_timetable')
    
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
                              task_description=task_description)
    
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

@app.route('/remove_timetable', methods=['POST'])
def remove_timetable():
    """Remove a subject from timetable database"""
    day = int(request.form.get('day', 0))
    time = request.form.get('time', '')
    
    try:
        conn = get_db_connection()
        conn.execute(
            'DELETE FROM timetable WHERE day = ? AND time_slot = ?',
            (day, time)
        )
        conn.commit()
        conn.close()
        
        return redirect('/edit_timetable')
    
    except Exception as e:
        return f'<h1>Error removing from timetable: {str(e)}</h1><p><a href="/edit_timetable">Go back</a></p>'

@app.route('/clear_timetable', methods=['POST'])
def clear_timetable():
    """Clear all timetable data"""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM timetable')
        conn.commit()
        conn.close()
        
        return redirect('/edit_timetable')
    
    except Exception as e:
        return f'<h1>Error clearing timetable: {str(e)}</h1><p><a href="/edit_timetable">Go back</a></p>'

if __name__ == '__main__':
    app.run(debug=True)