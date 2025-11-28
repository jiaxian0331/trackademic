# Databases/notes.py
import sqlite3

def create_notes_database():
    """Create and populate a SQLite database for Trackademic"""
    
    conn = sqlite3.connect('trackademic.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        note_id INTEGER PRIMARY KEY,
        subject_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file BLOB
    )
    ''')
    
    notes = [
        ('GNB1114', '1', 'trackademic.pdf', 'Databases'),
    ]
    
    cursor.executemany(
        '''INSERT OR IGNORE INTO notes
        (subject_id, user_id, file_name, file)
        VALUES (?, ?, ?, ?)''',
        notes
    )

    conn.commit()
    print("Notes Database created successfully!")
    
    conn.close()

if __name__ == "__main__":
    create_notes_database()