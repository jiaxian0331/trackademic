from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def init_db():
    db = sqlite3.connect("database.db")
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            filename TEXT,
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

init_db()

def get_comments_for_post(post_id):
    db = sqlite3.connect("database.db")
    cursor = db.execute(
        "SELECT id, username, comment, user_id FROM comments WHERE post_id=? ORDER BY created_at ASC",
        (post_id,)
    )
    comments = cursor.fetchall()
    db.close()
    return comments

@app.route("/")
def home():
    return redirect("/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        db = sqlite3.connect("database.db")
        try:
            db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
            db.commit()
        except sqlite3.IntegrityError:
            db.close()
            return render_template("signup.html", error="Email already exists.")
        db.close()
        return redirect("/login")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = sqlite3.connect("database.db")
        cursor = db.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        db.close()
        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Wrong email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

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
        db = sqlite3.connect("database.db")
        db.execute("INSERT INTO posts (user_id, content, filename) VALUES (?, ?, ?)", (user_id, content, filename))
        db.commit()
        db.close()
        return redirect("/dashboard")

    db = sqlite3.connect("database.db")
    
    # --- UPDATED: Only show folders that have at least one post saved in them ---
    cursor = db.execute("""
        SELECT DISTINCT folders.id, folders.folder_name 
        FROM folders 
        JOIN saved_posts ON folders.id = saved_posts.folder_id 
        WHERE folders.user_id=?
    """, (user_id,))
    folders = cursor.fetchall()

    query = """
        SELECT 
            posts.id, posts.content, posts.filename, users.username, posts.user_id,
            EXISTS(SELECT 1 FROM saved_posts WHERE post_id = posts.id AND user_id = ?)
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
    
    posts_with_comments = []
    for post in posts:
        comments = get_comments_for_post(post[0])
        posts_with_comments.append((*post, comments))

    db.close()
    return render_template("dashboard.html", username=username, posts=posts_with_comments, folders=folders, search_query=search_query)

@app.route("/save_post/<int:post_id>", methods=["POST"])
def save_post(post_id):
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    folder_id = request.form.get("folder_id")
    new_folder_name = request.form.get("new_folder_name")

    db = sqlite3.connect("database.db")
    if new_folder_name and new_folder_name.strip():
        cursor = db.execute("INSERT INTO folders (user_id, folder_name) VALUES (?, ?)", 
                            (user_id, new_folder_name.strip()))
        folder_id = cursor.lastrowid
    
    if folder_id:
        db.execute("INSERT INTO saved_posts (user_id, post_id, folder_id) VALUES (?, ?, ?)", 
                   (user_id, post_id, folder_id))
        db.commit()
    db.close()
    return redirect("/dashboard")

@app.route("/saved")
def saved_posts():
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    search_query = request.args.get('search', '')
    db = sqlite3.connect("database.db")
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
    return render_template("saved.html", organized=organized, username=session["username"], search_query=search_query)

@app.route("/unsave/<int:sp_id>", methods=["POST"])
def unsave(sp_id):
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    db = sqlite3.connect("database.db")
    
    # --- UPDATED: Check if folder becomes empty after deletion ---
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
    return redirect("/saved")

@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "user_id" not in session: return redirect("/login")
    user_id = session["user_id"]
    db = sqlite3.connect("database.db")
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
        # Optional: Add a cleanup for empty folders here if post deletion empties a folder
    db.commit()
    db.close()
    return redirect("/dashboard")

@app.route("/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    if "user_id" not in session: return redirect("/login")
    comment_text = request.form.get("comment")
    if comment_text:
        db = sqlite3.connect("database.db")
        db.execute("INSERT INTO comments (post_id, user_id, username, comment) VALUES (?, ?, ?, ?)",
                   (post_id, session["user_id"], session["username"], comment_text))
        db.commit()
        db.close()
    return redirect("/dashboard")

@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    if "user_id" not in session: return redirect("/login")
    db = sqlite3.connect("database.db")
    cursor = db.execute("SELECT user_id FROM comments WHERE id=?", (comment_id,))
    result = cursor.fetchone()
    if result and result[0] == session["user_id"]:
        db.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        db.commit()
    db.close()
    return redirect("/dashboard")

if __name__ == "__main__":
    app.run(debug=True)
