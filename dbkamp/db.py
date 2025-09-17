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
    # Notification preferences
    ensure_column('notify_email', 'notify_email INTEGER DEFAULT 1')
    ensure_column('notify_digest', "notify_digest TEXT DEFAULT 'weekly'")
    ensure_column('notify_webhook', 'notify_webhook TEXT')
    # admin flag
    ensure_column('is_admin', 'is_admin INTEGER DEFAULT 0')
    conn.commit()
    conn.close()
    # ensure API tokens table exists
    ensure_api_tokens_table()
    ensure_uploads_table()
    ensure_groups_tables()
    ensure_projects_tables()
    ensure_environments_table()
    ensure_audit_table()


def ensure_api_tokens_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS api_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT,
        token_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        revoked_at TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def ensure_uploads_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT,
        status TEXT,
        message TEXT,
        chunks_indexed INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def ensure_groups_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS group_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        project_name TEXT NOT NULL,
        linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    

def ensure_projects_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        repo_url TEXT,
        orchestration TEXT,
        config TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        body TEXT,
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        due_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    # project members table
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS project_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def ensure_environments_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS environments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        target TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS env_vars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        environment_id INTEGER NOT NULL,
        var_key TEXT NOT NULL,
        var_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def ensure_audit_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        actor_user_id INTEGER,
        details TEXT,
        ip TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def create_environment(project_id: int, name: str, target: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO environments (project_id, name, target) VALUES (?, ?, ?)', (project_id, name, target))
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    try:
        record_audit('environment.create', actor_user_id=None, details=f'project_id={project_id}, env={name}')
    except Exception:
        pass
    return eid


def list_environments(project_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, target, created_at FROM environments WHERE project_id = ? ORDER BY created_at DESC', (project_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_env_var(environment_id: int, key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    # upsert simple approach: try update, else insert
    cur.execute('UPDATE env_vars SET var_value = ? WHERE environment_id = ? AND var_key = ?', (value, environment_id, key))
    if cur.rowcount == 0:
        cur.execute('INSERT INTO env_vars (environment_id, var_key, var_value) VALUES (?, ?, ?)', (environment_id, key, value))
    conn.commit()
    conn.close()
    return True


def list_env_vars(environment_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, var_key, var_value, created_at FROM env_vars WHERE environment_id = ? ORDER BY created_at DESC', (environment_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_audit(event_type: str, actor_user_id: int = None, details: str = None, ip: str = None):
    """Record an audit event."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO audit_logs (event_type, actor_user_id, details, ip) VALUES (?, ?, ?, ?)', (event_type, actor_user_id, details, ip))
    conn.commit()
    conn.close()


def list_audit_logs(limit: int = 200):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, event_type, actor_user_id, details, ip, created_at FROM audit_logs ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_project(name: str, repo_url: str = None, orchestration: str = None, config: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO projects (name, repo_url, orchestration, config) VALUES (?, ?, ?, ?)', (name, repo_url, orchestration, config))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    try:
        record_audit('project.create', actor_user_id=None, details=f'project={name}, repo={repo_url}')
    except Exception:
        pass
    return pid


def list_projects(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, repo_url, orchestration, created_at FROM projects ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, repo_url, orchestration, config, created_at FROM projects WHERE id = ?', (project_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_issue(project_id: int, title: str, body: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO issues (project_id, title, body) VALUES (?, ?, ?)', (project_id, title, body))
    conn.commit()
    conn.close()
    return True


def list_issues(project_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, title, body, status, created_at FROM issues WHERE project_id = ? ORDER BY created_at DESC', (project_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_milestone(project_id: int, title: str, due_date: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO milestones (project_id, title, due_date) VALUES (?, ?, ?)', (project_id, title, due_date))
    conn.commit()
    conn.close()
    return True


def list_milestones(project_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, title, due_date, created_at FROM milestones WHERE project_id = ? ORDER BY created_at DESC', (project_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_project_member(project_id: int, user_id: int, role: str = 'member'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)', (project_id, user_id, role))
    conn.commit()
    conn.close()
    try:
        record_audit('project.member.add', actor_user_id=None, details=f'project_id={project_id}, user_id={user_id}, role={role}')
    except Exception:
        pass
    return True


def list_project_members(project_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT pm.id, pm.user_id, pm.role, u.email, u.full_name, pm.added_at FROM project_members pm LEFT JOIN users u ON u.id = pm.user_id WHERE pm.project_id = ? ORDER BY pm.added_at DESC', (project_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_group(name: str, description: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO groups (name, description) VALUES (?, ?)', (name, description))
    conn.commit()
    gid = cur.lastrowid
    conn.close()
    try:
        record_audit('group.create', actor_user_id=None, details=f'group={name}')
    except Exception:
        pass
    return gid


def list_groups(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, description, created_at FROM groups ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_group_member(group_id: int, user_id: int, role: str = 'member'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, ?)', (group_id, user_id, role))
    conn.commit()
    conn.close()
    return True


def list_group_members(group_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT gm.id, gm.user_id, gm.role, u.email, u.full_name FROM group_members gm LEFT JOIN users u ON u.id = gm.user_id WHERE gm.group_id = ? ORDER BY gm.added_at', (group_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def link_project_to_group(group_id: int, project_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO group_projects (group_id, project_name) VALUES (?, ?)', (group_id, project_name))
    conn.commit()
    conn.close()
    return True


def list_group_projects(group_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, project_name, linked_at FROM group_projects WHERE group_id = ? ORDER BY linked_at DESC', (group_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_upload(user_id: int, filename: str, status: str, message: str = None, chunks_indexed: int = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO uploads (user_id, filename, status, message, chunks_indexed) VALUES (?, ?, ?, ?, ?)', (user_id, filename, status, message, chunks_indexed))
    conn.commit()
    conn.close()
    try:
        record_audit('upload.record', actor_user_id=user_id, details=f'{filename} status={status} msg={message}')
    except Exception:
        pass


def list_uploads_for_user(user_id: int, limit: int = 20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, filename, status, message, chunks_indexed, created_at FROM uploads WHERE user_id = ? ORDER BY created_at DESC LIMIT ?', (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_api_token(user_id: int, name: str, token_plain: str):
    """Store a hashed token and return True on success."""
    from werkzeug.security import generate_password_hash
    token_hash = generate_password_hash(token_plain)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO api_tokens (user_id, name, token_hash) VALUES (?, ?, ?)', (user_id, name, token_hash))
    conn.commit()
    conn.close()
    try:
        record_audit('api.token.create', actor_user_id=user_id, details=f'name={name}')
    except Exception:
        pass
    return True


def list_api_tokens(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, created_at, revoked_at FROM api_tokens WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def revoke_api_token(token_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM api_tokens WHERE id = ? AND user_id = ?', (token_id, user_id))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute('UPDATE api_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = ?', (token_id,))
    conn.commit()
    conn.close()
    try:
        record_audit('api.token.revoke', actor_user_id=user_id, details=f'token_id={token_id}')
    except Exception:
        pass
    return True


def create_user(email: str, password: str) -> bool:
    """Create a new user; returns True on success, False if email exists."""
    pw_hash = generate_password_hash(password)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, pw_hash))
        conn.commit()
        try:
            record_audit('user.create', actor_user_id=None, details=f'email={email}')
        except Exception:
            pass
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


def update_password(user_id: int, new_password: str):
    """Update a user's password (hashes new password). Returns True on success."""
    pw_hash = generate_password_hash(new_password)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute('UPDATE users SET password = ? WHERE id = ?', (pw_hash, user_id))
    conn.commit()
    conn.close()
    return True


def get_user_preferences(user_id: int):
    """Return notification preference fields for a user as a dict."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT notify_email, notify_digest, notify_webhook FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'notify_email': bool(row['notify_email']) if row['notify_email'] is not None else True,
        'notify_digest': row['notify_digest'] or 'weekly',
        'notify_webhook': row['notify_webhook'] or ''
    }


def update_notification_preferences(user_id: int, notify_email: bool, notify_digest: str, notify_webhook: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute('UPDATE users SET notify_email = ?, notify_digest = ?, notify_webhook = ? WHERE id = ?', (
        1 if notify_email else 0, notify_digest, notify_webhook, user_id
    ))
    conn.commit()
    conn.close()
    return True
