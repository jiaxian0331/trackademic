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
        CREATE TABLE IF NOT EXISTS saved_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            post_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
    """)

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
            db.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
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
        cursor = db.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )
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

    if request.method == "POST":
        content = request.form.get("content")
        file = request.files.get("file")
        filename = None

        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db = sqlite3.connect("database.db")
        db.execute(
            "INSERT INTO posts (user_id, content, filename) VALUES (?, ?, ?)",
            (user_id, content, filename)
        )
        db.commit()
        db.close()

        return redirect("/dashboard")

    db = sqlite3.connect("database.db")
    cursor = db.execute("""
        SELECT 
            posts.id, 
            posts.content, 
            posts.filename, 
            users.username,
            posts.user_id,
            EXISTS(
                SELECT 1 FROM saved_posts 
                WHERE saved_posts.post_id = posts.id AND saved_posts.user_id = ?
            ) AS is_saved
        FROM posts 
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """, (user_id,))
    posts = cursor.fetchall()
    posts_with_comments = []

    for post in posts:
        comments = get_comments_for_post(post[0])
        posts_with_comments.append((*post, comments))

    db.close()
    return render_template("dashboard.html", username=username, posts=posts_with_comments)

@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = sqlite3.connect("database.db")
    cursor = db.execute("SELECT filename FROM posts WHERE id=? AND user_id=?", (post_id, user_id))
    result = cursor.fetchone()

    if result:
        filename = result[0]
        if filename:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(path):
                os.remove(path)
        db.execute("DELETE FROM posts WHERE id=? AND user_id=?", (post_id, user_id))
        db.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        db.execute("DELETE FROM saved_posts WHERE post_id=?", (post_id,))
        db.commit()
    db.close()
    return redirect("/dashboard")

@app.route("/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    if "user_id" not in session:
        return redirect("/login")

    comment_text = request.form.get("comment")
    if comment_text:
        db = sqlite3.connect("database.db")
        db.execute(
            "INSERT INTO comments (post_id, user_id, username, comment) VALUES (?, ?, ?, ?)",
            (post_id, session["user_id"], session["username"], comment_text)
        )
        db.commit()
        db.close()
    return redirect("/dashboard")

@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = sqlite3.connect("database.db")
    cursor = db.execute("SELECT user_id FROM comments WHERE id=?", (comment_id,))
    result = cursor.fetchone()
    if result and result[0] == user_id:
        db.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        db.commit()
    db.close()
    return redirect("/dashboard")

@app.route("/save_post/<int:post_id>", methods=["POST"])
def save_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = sqlite3.connect("database.db")
    cursor = db.execute("SELECT 1 FROM saved_posts WHERE user_id=? AND post_id=?", (user_id, post_id))
    exists = cursor.fetchone()
    if not exists:
        db.execute("INSERT INTO saved_posts (user_id, post_id) VALUES (?, ?)", (user_id, post_id))
        db.commit()
    db.close()
    return redirect("/dashboard")

@app.route("/unsave_post/<int:post_id>", methods=["POST"])
def unsave_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = sqlite3.connect("database.db")
    db.execute("DELETE FROM saved_posts WHERE user_id=? AND post_id=?", (user_id, post_id))
    db.commit()
    db.close()
    return redirect("/saved")

@app.route("/saved")
def saved_posts():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    db = sqlite3.connect("database.db")
    cursor = db.execute("""
        SELECT posts.id, posts.content, posts.filename, users.username
        FROM posts
        JOIN saved_posts ON posts.id = saved_posts.post_id
        JOIN users ON posts.user_id = users.id
        WHERE saved_posts.user_id = ?
        ORDER BY saved_posts.id DESC
    """, (user_id,))
    posts = cursor.fetchall()
    db.close()

    return render_template("saved.html", posts=posts, username=session.get("username", "User"))

if __name__ == "__main__":
    app.run(debug=True)
