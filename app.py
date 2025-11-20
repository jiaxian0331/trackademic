from flask import Flask, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('school_subjects.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return '''
    <h1>Subjects Database</h1>
    <ul>
        <li><a href="/subjects">View All Subjects</a></li>
        <li><a href="/add-subject">Add New Subject</a></li>
        <li><a href="/create-db">Create/Reset Database</a></li>
    </ul>
    '''

@app.route('/subjects')
def list_subjects():
    try:
        conn = get_db_connection()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_id').fetchall()
        conn.close()
        
        if not subjects:
            return '<h1>No subjects found.</h1><p><a href="/create-db">Create database first</a></p>'
        
        html = '<h1>All Subjects</h1>'
        html += '<p><a href="/add-subject" style="background: grey; color: white; padding: 10px; text-decoration: none; border-radius: 5px;">+ Add New Subject</a></p>'
        html += '<table border="1" style="border-collapse: collapse; width: 100%; margin: 20px 0;">'
        html += '<tr style="background-color: #f2f2f2;"><th>ID</th><th>Code</th><th>Subject Name</th><th>Credit Hours</th><th>Actions</th></tr>'
        
        for subject in subjects:
            html += f'<tr>'
            html += f'<td style="padding: 8px; text-align: center;">{subject["subject_id"]}</td>'
            html += f'<td style="padding: 8px;">{subject["subject_code"]}</td>'
            html += f'<td style="padding: 8px;">{subject["subject_name"]}</td>'
            html += f'<td style="padding: 8px; text-align: center;">{subject["credit_hours"]}</td>'
            html += f'<td style="padding: 8px; text-align: center;">'
            html += f'<a href="/edit-subject/{subject["subject_id"]}" style="background: grey; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin: 0 5px;">Edit</a>'
            html += f'<a href="/delete-subject/{subject["subject_id"]}" style="background: grey; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; margin: 0 5px;" onclick="return confirm(\'Are you sure you want to delete this subject?\')">Delete</a>'
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
        # Get form data
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
            return f'<h1>Error adding subject: {str(e)}</h1><p><a href="/add-subject">Try again</a></p>'
    
    # GET request - show the form
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
            <input type="submit" value="Add Subject" style="background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
            <a href="/subjects" style="background: #ccc; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Cancel</a>
        </div>
    </form>
    '''

@app.route('/edit-subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Update the subject
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
            return f'<h1>Error updating subject: {str(e)}</h1><p><a href="/edit-subject/{subject_id}">Try again</a></p>'
    
    # GET request - show the form with current data
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
        return redirect('/subjects')
    except Exception as e:
        return f'<h1>Error deleting subject: {str(e)}</h1><p><a href="/subjects">Back to subjects</a></p>'

@app.route('/create-db')
def create_database_route():
    try:
        import Databases.database
        Databases.database.create_database()
        return '''
        <h1>Database created successfully! ✅</h1>
        <p><a href="/subjects">View Subjects</a></p>
        <p><a href="/">Back to Home</a></p>
        '''
    except Exception as e:
        return f'<h1>Error: {str(e)}</h1>'

if __name__ == '__main__':
    app.run(debug=True)