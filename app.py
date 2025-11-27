from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# ------------------ Initialize Database ------------------
def init_db():
    db = sqlite3.connect("database.db")
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            password TEXT
        )
    """)
    db.close()

init_db()

# ------------------ Home Route ------------------
@app.route("/")
def home():
    return redirect("/signup")

# ------------------ Signup Page ------------------
@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/signup", methods=["POST"])
def signup_post():
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    db = sqlite3.connect("database.db")
    db.execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        (username, email, password)
    )
    db.commit()
    db.close()

    return redirect("/login")

# ------------------ Login Page ------------------
@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_post():
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
        return render_template("dashboard.html", username=user[1])
    else:
        return render_template("login.html", error="Wrong email or password.")

# ------------------ Dashboard Page ------------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", username="User")

# ------------------ Run App ------------------
if __name__ == "__main__":
    app.run(debug=True)
