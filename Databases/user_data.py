# Databases/user_data.py
import sqlite3

def create_user_database():
    """Create and populate a SQLite database for Trackademic"""
    
    conn = sqlite3.connect('trackademic.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_data (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')
    
    user_data = [
        ('jiaxian0331', 'hoejiaxian@gmail.com', 'jiaxian0000'),
    ]
    
    cursor.executemany(
        '''INSERT OR IGNORE INTO user_data 
        (username, email, password) 
        VALUES (?, ?, ?)''',
        user_data
    )

    conn.commit()
    print("User Database created successfully!")
    
    conn.close()

if __name__ == "__main__":
    create_user_database()