import json
import os
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "historical_chat.db"
JSON_PATH = BASE_DIR / "personas.json"


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def load_personas():
    try:
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: Could not find '{JSON_PATH}'. Falling back to an empty dictionary.")
        return {}
    except json.JSONDecodeError:
        print(f"ERROR: '{JSON_PATH}' contains invalid JSON formatting. Check your commas!")
        return {}


def save_new_persona(character_name, character_data):
    current_personas = load_personas()
    current_personas[character_name] = character_data
    JSON_PATH.write_text(json.dumps(current_personas, indent=4, ensure_ascii=False), encoding="utf-8")


ACTIVE_PERSONAS = load_personas()
BOOTSTRAP_ADMIN_CREDENTIALS = None


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        '''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password_hash TEXT,
                  is_admin INTEGER DEFAULT 0,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)'''
    )

    conn.execute(
        '''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  character_id INTEGER,
                  sender TEXT,
                  content TEXT,
                  context_key TEXT,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))'''
    )

    conn.execute(
        '''CREATE TABLE IF NOT EXISTS characters
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  system_prompt TEXT,
                  bio TEXT,
                  language TEXT,
                  character_type TEXT,
                  source_title TEXT,
                  source_author TEXT,
                  source_url TEXT,
                  avatar_path TEXT,
                  is_custom INTEGER DEFAULT 0,
                  created_by_user_id INTEGER,
                  is_hidden INTEGER DEFAULT 0,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  updated_at TEXT DEFAULT CURRENT_TIMESTAMP)'''
    )

    conn.execute(
        '''CREATE TABLE IF NOT EXISTS character_memory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  character_id INTEGER NOT NULL,
                  summary TEXT DEFAULT '',
                  tone TEXT DEFAULT 'neutral',
                  last_topic TEXT DEFAULT '',
                  interaction_count INTEGER DEFAULT 0,
                  last_interaction_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(user_id, character_id),
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(character_id) REFERENCES characters(id))'''
    )

    ensure_users_columns(conn)
    ensure_messages_columns(conn)
    ensure_characters_columns(conn)
    ensure_character_memory_columns(conn)

    conn.execute("UPDATE characters SET is_custom = COALESCE(is_custom, 0), is_hidden = COALESCE(is_hidden, 0), avatar_path = COALESCE(avatar_path, '')")
    conn.execute("UPDATE users SET is_admin = COALESCE(is_admin, 0)")
    conn.execute("UPDATE messages SET created_at = COALESCE(created_at, ?)", (now_iso(),))
    conn.execute("UPDATE character_memory SET summary = COALESCE(summary, ''), tone = COALESCE(tone, 'neutral'), last_topic = COALESCE(last_topic, ''), interaction_count = COALESCE(interaction_count, 0), last_interaction_at = COALESCE(last_interaction_at, ?)", (now_iso(),))

    seed_builtin_characters(conn)
    bootstrap_admin_account(conn)
    conn.commit()
    conn.close()


def ensure_users_columns(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    for column_name, column_type in {
        "is_admin": "INTEGER",
        "created_at": "TEXT",
    }.items():
        if column_name not in columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")


def ensure_messages_columns(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
    for column_name, column_type in {
        "character_id": "INTEGER",
        "context_key": "TEXT",
        "created_at": "TEXT",
    }.items():
        if column_name not in columns:
            conn.execute(f"ALTER TABLE messages ADD COLUMN {column_name} {column_type}")


def ensure_characters_columns(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(characters)").fetchall()}
    for column_name, column_type in {
        "language": "TEXT",
        "character_type": "TEXT",
        "source_title": "TEXT",
        "source_author": "TEXT",
        "source_url": "TEXT",
        "avatar_path": "TEXT",
        "is_custom": "INTEGER",
        "created_by_user_id": "INTEGER",
        "is_hidden": "INTEGER",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }.items():
        if column_name not in columns:
            conn.execute(f"ALTER TABLE characters ADD COLUMN {column_name} {column_type}")


def ensure_character_memory_columns(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(character_memory)").fetchall()}
    for column_name, column_type in {
        "summary": "TEXT",
        "tone": "TEXT",
        "last_topic": "TEXT",
        "interaction_count": "INTEGER",
        "last_interaction_at": "TEXT",
    }.items():
        if column_name not in columns:
            conn.execute(f"ALTER TABLE character_memory ADD COLUMN {column_name} {column_type}")


def bootstrap_admin_account(conn):
    global BOOTSTRAP_ADMIN_CREDENTIALS
    has_admin = conn.execute("SELECT 1 FROM users WHERE is_admin = 1 LIMIT 1").fetchone()
    if has_admin:
        BOOTSTRAP_ADMIN_CREDENTIALS = None
        return None

    username = (os.getenv("HISTORICAL_DEBATE_ADMIN_USERNAME", "traffic_admin") or "traffic_admin").strip()
    password = os.getenv("HISTORICAL_DEBATE_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    base_username = username or "traffic_admin"
    candidate = base_username
    suffix = 2
    while conn.execute("SELECT 1 FROM users WHERE lower(username) = lower(?)", (candidate,)).fetchone():
        candidate = f"{base_username}_{suffix}"
        suffix += 1

    conn.execute(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
        (candidate, generate_password_hash(password)),
    )
    BOOTSTRAP_ADMIN_CREDENTIALS = {"username": candidate, "password": password}
    return BOOTSTRAP_ADMIN_CREDENTIALS


def seed_builtin_characters(conn):
    conn.execute("DELETE FROM characters WHERE name = ?", ("Hitler",))
    personas = [
        (
            name,
            data.get("system_prompt", ""),
            data.get("bio", ""),
            data.get("language", "English"),
            "historical",
            data.get("source_title"),
            data.get("source_author"),
            data.get("source_url"),
            data.get("avatar_path") or f"resources/{character_default_avatar(name)}",
            0,
        )
        for name, data in ACTIVE_PERSONAS.items()
    ]
    conn.executemany(
        """
        INSERT INTO characters (name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path, is_custom)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            system_prompt = excluded.system_prompt,
            bio = excluded.bio,
            language = excluded.language,
            character_type = excluded.character_type,
            source_title = excluded.source_title,
            source_author = excluded.source_author,
            source_url = excluded.source_url,
            avatar_path = COALESCE(characters.avatar_path, excluded.avatar_path),
            is_custom = excluded.is_custom,
            updated_at = CURRENT_TIMESTAMP
        """,
        personas,
    )


# -------------------------
# Users / auth
# -------------------------

def create_user(username, password, is_admin=False):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), 1 if is_admin else 0),
        )
        conn.commit()
        return get_user_by_id(cursor.lastrowid)
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, username, password_hash, is_admin, created_at FROM users WHERE id = ?",
        [user_id],
    ).fetchone()
    conn.close()
    return row


def get_user_by_username(username):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, username, password_hash, is_admin, created_at FROM users WHERE lower(username) = lower(?)",
        [username],
    ).fetchone()
    conn.close()
    return row


def get_user_count():
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count


def authenticate_user(username, password):
    user = get_user_by_username(username)
    if not user:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


# -------------------------
# Messages and history
# -------------------------

def save_msg(user_id, sender, content, context_key=None, character_id=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (user_id, character_id, sender, content, context_key, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, character_id, sender, content, context_key, now_iso()),
    )
    conn.commit()
    conn.close()


def get_history(user_id, allowed_senders=None, context_key=None, limit=24):
    conn = sqlite3.connect(DB_PATH)
    params = [user_id]
    sender_filter = ""
    if allowed_senders:
        senders = sorted(set(allowed_senders) | {"User"})
        placeholders = ",".join("?" for _ in senders)
        sender_filter = f" AND sender IN ({placeholders})"
        params.extend(senders)
    context_filter = ""
    if context_key:
        context_filter = " AND context_key = ?"
        params.append(context_key)

    limit_clause = ""
    if limit:
        limit_clause = " LIMIT ?"
        params.append(int(limit))

    cursor = conn.execute(
        f"SELECT sender, content FROM messages WHERE user_id = ?{sender_filter}{context_filter} ORDER BY id DESC{limit_clause}",
        params,
    )
    rows = cursor.fetchall()
    conn.close()
    rows.reverse()
    return [{"role": "user" if r[0] == "User" else "assistant", "content": r[1]} for r in rows]


# -------------------------
# Characters
# -------------------------

def get_character_record_by_id(char_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT id, name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path,
               is_custom, created_by_user_id, is_hidden, created_at, updated_at
        FROM characters
        WHERE id = ?
        """,
        [char_id],
    ).fetchone()
    conn.close()
    return row


def get_persona_by_id(char_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT id, name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path,
               is_custom, created_by_user_id, is_hidden, created_at, updated_at
        FROM characters
        WHERE id = ? AND is_hidden = 0
        """,
        [char_id],
    ).fetchone()
    conn.close()
    return row


def get_character_by_name(name, include_hidden=True):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = """
        SELECT id, name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path,
               is_custom, created_by_user_id, is_hidden, created_at, updated_at
        FROM characters
        WHERE lower(name) = lower(?)
    """
    if not include_hidden:
        query += " AND is_hidden = 0"
    row = conn.execute(query, [name]).fetchone()
    conn.close()
    return row


def get_custom_character_by_id(char_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT id, name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path,
               is_custom, created_by_user_id, is_hidden, created_at, updated_at
        FROM characters
        WHERE id = ? AND is_custom = 1 AND is_hidden = 0
        """,
        [char_id],
    ).fetchone()
    conn.close()
    return row


def get_all_characters(include_hidden=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = """
        SELECT id, name, system_prompt, bio, language, character_type, is_custom, created_by_user_id,
               is_hidden, source_title, source_author, source_url, avatar_path
        FROM characters
    """
    if not include_hidden:
        query += " WHERE is_hidden = 0"
    query += " ORDER BY is_custom ASC, name COLLATE NOCASE ASC"
    chars = conn.execute(query).fetchall()
    conn.close()
    return chars


def save_custom_character(name, system_prompt, bio, language, character_type, created_by_user_id, source_title=None, source_author=None, source_url=None, avatar_path=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        INSERT INTO characters (name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path, is_custom, created_by_user_id, is_hidden)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
        """,
        (name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path, created_by_user_id),
    )
    conn.commit()
    char_id = cursor.lastrowid
    conn.close()
    return get_persona_by_id(char_id)


def update_custom_character(char_id, name, system_prompt, bio, language, character_type, source_title=None, source_author=None, source_url=None, avatar_path=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        UPDATE characters
        SET name = ?,
            system_prompt = ?,
            bio = ?,
            language = ?,
            character_type = ?,
            source_title = ?,
            source_author = ?,
            source_url = ?,
            avatar_path = ?,
            updated_at = ?
        WHERE id = ? AND is_custom = 1 AND is_hidden = 0
        """,
        (name, system_prompt, bio, language, character_type, source_title, source_author, source_url, avatar_path, now_iso(), char_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def hide_character(char_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "UPDATE characters SET is_hidden = 1, updated_at = ? WHERE id = ?",
        (now_iso(), char_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# -------------------------
# Character memory
# -------------------------

def get_character_memory(user_id, character_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT id, user_id, character_id, summary, tone, last_topic, interaction_count, last_interaction_at
        FROM character_memory
        WHERE user_id = ? AND character_id = ?
        """,
        [user_id, character_id],
    ).fetchone()
    conn.close()
    return row


def upsert_character_memory(user_id, character_id, summary, tone, last_topic):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO character_memory (user_id, character_id, summary, tone, last_topic, interaction_count, last_interaction_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, character_id) DO UPDATE SET
            summary = excluded.summary,
            tone = excluded.tone,
            last_topic = excluded.last_topic,
            interaction_count = COALESCE(character_memory.interaction_count, 0) + 1,
            last_interaction_at = excluded.last_interaction_at
        """,
        (user_id, character_id, summary, tone, last_topic, 1, now_iso()),
    )
    conn.commit()
    conn.close()
    return True


def character_default_avatar(name):
    mapping = {
        "Fidel Castro": "Castro.jpg",
        "Richard Nixon": "Nixon.jpg",
        "Winston Churchill": "Churchill.jpg",
        "Giuseppe Garibaldi": "Garibaldi.jpg",
        "Socrates": "Socrates.jpg",
        "Robert the Bruce": "Bruce.jpg",
        "Edward II of England": "Edward.jpg",
        "Queen Victoria": "Victoria.jpg",
        "Elizabeth I": "Elizabeth_I.jpg",
        "Alan Turing": "Turing.jpg",
        "Margaret Thatcher": "Thatcher.jpg",
        "Ernesto Che Guevara": "Che.jpg",
    }
    return mapping.get(name, "")
