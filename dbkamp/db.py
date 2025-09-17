import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / 'dbkamp.sqlite3'


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        company TEXT,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    # Ensure columns exist (for upgrades)
    existing = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    def ensure_column(col, col_def):
        if col not in existing:
            try:
                conn.execute(f'ALTER TABLE users ADD COLUMN {col_def}')
            except Exception:
                pass

    ensure_column('full_name', 'full_name TEXT')
    ensure_column('company', 'company TEXT')
    ensure_column('phone', 'phone TEXT')
    conn.commit()
    conn.close()


def create_user(email: str, password: str) -> bool:
    """Create a new user; returns True on success, False if email exists."""
    pw_hash = generate_password_hash(password)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, pw_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def authenticate_user(email: str, password: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    if check_password_hash(row['password'], password):
        return dict(row)
    return None


def update_user_profile(user_id: int, full_name: str = None, company: str = None, phone: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute('UPDATE users SET full_name = COALESCE(?, full_name), company = COALESCE(?, company), phone = COALESCE(?, phone) WHERE id = ?', (full_name, company, phone, user_id))
    conn.commit()
    conn.close()
    return True
