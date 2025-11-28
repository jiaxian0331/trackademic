# Databases/gpa.py
import sqlite3

def create_gpa_database():
    """Create and populate a SQLite database for Trackademic"""
    
    conn = sqlite3.connect('trackademic.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS gpa (
        trimester_id INTEGER PRIMARY KEY,
        trimester TEXT NOT NULL UNIQUE,
        gpa REAL NOT NULL CHECK (gpa >= 0.0 AND gpa <= 4.0)
    )
    ''')
    
    gpa = [
        ('Trimester 2510', '3.73'),
    ]
    
    cursor.executemany(
        '''INSERT OR IGNORE INTO gpa
        (trimester, gpa) 
        VALUES (?, ?)''',
        gpa
    )

    conn.commit()
    print("GPA Database created successfully!")
    
    conn.close()

if __name__ == "__main__":
    create_gpa_database()