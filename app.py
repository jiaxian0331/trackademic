from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ------------------ Upload Folder ------------------
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ------------------ Initialize Database ------------------
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
    db.close()

init_db()

# ------------------ Home Route ------------------
@app.route("/")
def home():
    return redirect("/login")

# ------------------ Signup Page ------------------
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

# ------------------ Login Page ------------------
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

# ------------------ Logout ------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ------------------ Dashboard Page ------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    username = session["username"]

    # Handle new post
    if request.method == "POST":
        content = request.form.get("content")
        file = request.files.get("file")
        filename = None

        if file and file.filename != "":
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

    # Fetch posts
    db = sqlite3.connect("database.db")
    cursor = db.execute(
        "SELECT posts.id, posts.content, posts.filename, users.username, posts.user_id "
        "FROM posts JOIN users ON posts.user_id = users.id "
        "ORDER BY posts.id DESC"
    )
    posts = cursor.fetchall()
    db.close()

    return render_template("dashboard.html", username=username, posts=posts)

# ------------------ Delete Post ------------------
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
        if filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.execute("DELETE FROM posts WHERE id=? AND user_id=?", (post_id, user_id))
        db.commit()

    db.close()
    return redirect("/dashboard")

# ------------------ Run App ------------------
if __name__ == "__main__":
    app.run(debug=True)
