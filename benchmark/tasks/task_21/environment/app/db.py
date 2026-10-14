import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT DEFAULT 'user')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin', 'secret123', 'admin')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (2, 'alice', 'pass456', 'user')")
    conn.commit()
    conn.close()

def get_user(username: str):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT id, username, role FROM users WHERE username = '" + username + "'"
    cursor = conn.execute(query)
    row = cursor.fetchone()
    conn.close()
    return row

def authenticate(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT id FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor = conn.execute(query)
    row = cursor.fetchone()
    conn.close()
    return row is not None

def delete_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    query = "DELETE FROM users WHERE id = " + str(user_id)
    conn.execute(query)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("DB ready.")
