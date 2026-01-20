# Databases/notes.py
import sqlite3

def create_notes_database():
    """Create and populate a SQLite database for Trackademic"""
    
    conn = sqlite3.connect('trackademic.db')
    cursor = conn.cursor()
    
<<<<<<< HEAD
=======
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    
>>>>>>> jiaxian
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        note_id INTEGER PRIMARY KEY,
        subject_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
<<<<<<< HEAD
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
=======
        file BLOB,
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
    ''')
    
    # Fixed notes data - proper tuple structure
    notes = [
        (1, 1, 'business_notes.pdf', None),  # subject_id, user_id, file_name, file
        (2, 1, 'computing_notes.pdf', None),
        (3, 1, 'english_notes.pdf', None),
    ]
    
    try:
        cursor.executemany(
            '''INSERT OR IGNORE INTO notes
            (subject_id, user_id, file_name, file) 
            VALUES (?, ?, ?, ?)''',
            notes
        )
        conn.commit()
        print("Notes Database created successfully!")
    except sqlite3.IntegrityError as e:
        print(f"Warning: Some notes couldn't be inserted (foreign key constraint): {e}")
        conn.rollback()
    except Exception as e:
        print(f"Error creating notes database: {e}")
        conn.rollback()
    finally:
        conn.close()
>>>>>>> jiaxian

if __name__ == "__main__":
    create_notes_database()