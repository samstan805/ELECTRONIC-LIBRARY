import os
import sqlite3
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, send_from_directory)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change_this_secret_in_production"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

DB_PATH = os.path.join(BASE_DIR, "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 email TEXT UNIQUE,
                 password TEXT,
                 role TEXT,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS books (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 title TEXT,
                 author TEXT,
                 filename TEXT,
                 uploaded_by INTEGER,
                 uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(uploaded_by) REFERENCES users(id))""")
    conn.commit()
    conn.close()

init_db()

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/")
def root():
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Student")  # optional role selector on login
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        if user:
            if check_password_hash(user["password"], password):
                # successful login
                session['user_id'] = user["id"]
                session['email'] = user["email"]
                session['role'] = user["role"]
                session['name'] = user["name"]
                flash("Welcome, " + (user["name"] or user["email"]) , "success")
                # redirect based on role
                if user["role"] == "Admin":
                    return redirect(url_for('admin_dashboard'))
                elif user["role"] == "Librarian":
                    return redirect(url_for('librarian_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            else:
                # wrong password -> show recover prompt
                flash("Incorrect password. You can recover your password below.", "danger")
                return render_template("login.html", show_recover=True, email=email)
        else:
            flash("No account found with that email. Please register.", "danger")
            return render_template("login.html", show_recover=False, email=email)
    return render_template("login.html", show_recover=False, email="")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Student")
        if not email or not password:
            flash("Email and password required", "danger")
            return render_template("register.html")
        hashed = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         (name, email, hashed, role))
            conn.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    # This is a simple recovery flow: check email exists and display instructions.
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        if user:
            # In production you'd email a secure token link. Here we display a one-time reset token.
            flash(f"Password recovery: A password reset link has been (simulated) sent to {email}.", "info")
            return render_template("forgot_password.html", simulated=True, email=email)
        else:
            flash("No account found with that email.", "danger")
            return render_template("forgot_password.html", simulated=False)
    return render_template("forgot_password.html", simulated=False)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('login'))

@app.route("/student/dashboard")
@role_required("Student", "Admin", "Librarian")
def student_dashboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM books ORDER BY uploaded_at DESC")
    books = c.fetchall()
    conn.close()
    return render_template("student_dashboard.html", books=books)

@app.route("/librarian/dashboard")
@role_required("Librarian", "Admin")
def librarian_dashboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM books ORDER BY uploaded_at DESC")
    books = c.fetchall()
    conn.close()
    return render_template("librarian_dashboard.html", books=books)

@app.route("/admin/dashboard", methods=["GET", "POST"])
@role_required("Admin")
def admin_dashboard():
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        file = request.files.get("file")
        if not title or not author or not file:
            flash("Title, author and file are required.", "danger")
        else:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            c.execute("INSERT INTO books (title, author, filename, uploaded_by) VALUES (?, ?, ?, ?)",
                      (title, author, filename, session['user_id']))
            conn.commit()
            flash("Book uploaded.", "success")
    c.execute("SELECT * FROM books ORDER BY uploaded_at DESC")
    books = c.fetchall()
    conn.close()
    return render_template("admin_dashboard.html", books=books)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# basic route to download a book file
@app.route("/book/<int:book_id>/download")
@role_required("Student", "Librarian", "Admin")
def download_book(book_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = c.fetchone()
    conn.close()
    if not book:
        flash("Book not found", "danger")
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('uploaded_file', filename=book["filename"]))

if __name__ == "__main__":
    app.run(debug=True)