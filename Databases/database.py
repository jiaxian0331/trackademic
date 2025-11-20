# Databases/database.py
import sqlite3

def create_database():
    """Create and populate a SQLite database for subjects"""
    
    conn = sqlite3.connect('school_subjects.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL UNIQUE,
        subject_code TEXT UNIQUE,
        credit_hours INTEGER DEFAULT 3
    )
    ''')
    
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
        '''INSERT OR IGNORE INTO subjects 
        (subject_name, subject_code, credit_hours) 
        VALUES (?, ?, ?)''',
        subjects
    )

    conn.commit()
    print("Database 'school_subjects.db' created successfully!")
    
    conn.close()

if __name__ == "__main__":
    create_database()