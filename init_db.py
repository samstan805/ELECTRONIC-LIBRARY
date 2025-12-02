import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    # users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # books table
    c.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        author TEXT,
        filename TEXT,
        uploaded_by INTEGER,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(uploaded_by) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()
    print("Initialized DB")

if __name__ == "__main__":
    init_db()