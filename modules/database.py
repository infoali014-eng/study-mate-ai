import base64
import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from modules.security import is_path_inside


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "studymate.db"
LOCAL_SECRET_PATH = DATA_DIR / "app_secret.key"
load_dotenv(dotenv_path=BASE_DIR / ".env")


def get_connection():
    """Create a SQLite connection and return rows as dictionary-like objects."""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    """Create tables and run small safe migrations for older local databases."""
    with closing(get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL DEFAULT '',
                auth_provider TEXT DEFAULT 'email',
                role TEXT DEFAULT 'student',
                is_active INTEGER DEFAULT 1,
                study_goal TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploaded_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT DEFAULT 'PDF',
                extracted_text_path TEXT DEFAULT '',
                chunk_count INTEGER DEFAULT 0,
                extraction_method TEXT DEFAULT '',
                extraction_status TEXT DEFAULT '',
                warning_message TEXT DEFAULT '',
                page_count INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                topic TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                topic TEXT DEFAULT '',
                status TEXT DEFAULT 'New',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weak_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                weakness_score INTEGER DEFAULT 1,
                notes TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, subject_id, topic),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS revision_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                exam_date TEXT NOT NULL,
                preparation_level INTEGER NOT NULL,
                confidence_level INTEGER NOT NULL,
                weak_topics TEXT DEFAULT '',
                plan_text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                encrypted_api_key TEXT NOT NULL,
                key_suffix TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, provider),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS remember_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                provider TEXT DEFAULT '',
                model TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, document_id),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES uploaded_documents (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT DEFAULT 'Study Chat',
                chat_mode TEXT DEFAULT 'General Chat',
                subject_id INTEGER,
                document_ids_json TEXT DEFAULT '[]',
                context_label TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_archived INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_json TEXT DEFAULT '{}',
                metadata_json TEXT DEFAULT '{}',
                sources_json TEXT DEFAULT '[]',
                warning TEXT DEFAULT '',
                source_count INTEGER DEFAULT 0,
                suggestions_json TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                category TEXT DEFAULT 'custom',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                UNIQUE (user_id, memory_key),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id INTEGER NOT NULL,
                message_id INTEGER,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT DEFAULT '',
                mime_type TEXT DEFAULT '',
                file_size INTEGER DEFAULT 0,
                extracted_text TEXT DEFAULT '',
                extraction_method TEXT DEFAULT '',
                warning_message TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (message_id) REFERENCES chat_messages (id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER,
                session_type TEXT DEFAULT 'Focus',
                duration_minutes INTEGER NOT NULL,
                completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

        _add_missing_column(conn, "subjects", "user_id", "INTEGER")
        _add_missing_column(conn, "subjects", "is_deleted", "INTEGER DEFAULT 0")
        _ensure_subjects_table_allows_per_user_names(conn)
        _run_migrations(conn)
        _repair_subject_foreign_keys(conn)


def _add_missing_column(conn, table_name, column_name, column_definition):
    """Add a column when an older local database was created before it existed."""
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    column_names = [column["name"] for column in columns]
    if column_name not in column_names:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
        conn.commit()


def _ensure_subjects_table_allows_per_user_names(conn):
    """Replace an old global UNIQUE(name) subjects table with a user-scoped one."""
    index_rows = conn.execute("PRAGMA index_list(subjects)").fetchall()
    has_global_name_unique = False

    for index_row in index_rows:
        index_name = index_row["name"]
        is_unique = bool(index_row["unique"])
        if not is_unique:
            continue
        columns = [
            column["name"]
            for column in conn.execute(f"PRAGMA index_info({index_name})").fetchall()
        ]
        if columns == ["name"]:
            has_global_name_unique = True
            break

    if not has_global_name_unique:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE subjects RENAME TO subjects_old")
    conn.execute(
        """
        CREATE TABLE subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO subjects (id, user_id, name, description, created_at, is_deleted)
        SELECT id, user_id, name, description, created_at, 0
        FROM subjects_old
        """
    )
    conn.execute("DROP TABLE subjects_old")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _run_migrations(conn):
    """Add user scoping and indexes to older databases without losing records."""
    _add_missing_column(conn, "users", "password_hash", "TEXT NOT NULL DEFAULT ''")
    _add_missing_column(conn, "users", "auth_provider", "TEXT DEFAULT 'email'")
    _add_missing_column(conn, "users", "role", "TEXT DEFAULT 'student'")
    _add_missing_column(conn, "users", "is_active", "INTEGER DEFAULT 1")
    _add_missing_column(conn, "users", "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_missing_column(conn, "subjects", "user_id", "INTEGER")
    _add_missing_column(conn, "subjects", "is_deleted", "INTEGER DEFAULT 0")
    _add_missing_column(conn, "uploaded_documents", "user_id", "INTEGER")
    _add_missing_column(conn, "uploaded_documents", "file_type", "TEXT DEFAULT 'PDF'")
    _add_missing_column(conn, "uploaded_documents", "description", "TEXT DEFAULT ''")
    _add_missing_column(conn, "uploaded_documents", "is_deleted", "INTEGER DEFAULT 0")
    _add_missing_column(conn, "uploaded_documents", "extraction_method", "TEXT DEFAULT ''")
    _add_missing_column(conn, "uploaded_documents", "extraction_status", "TEXT DEFAULT ''")
    _add_missing_column(conn, "uploaded_documents", "warning_message", "TEXT DEFAULT ''")
    _add_missing_column(conn, "uploaded_documents", "page_count", "INTEGER DEFAULT 0")
    _add_missing_column(conn, "quiz_results", "user_id", "INTEGER")
    _add_missing_column(conn, "flashcards", "user_id", "INTEGER")
    _add_missing_column(conn, "flashcards", "status", "TEXT DEFAULT 'New'")
    _add_missing_column(conn, "weak_topics", "user_id", "INTEGER")
    _add_missing_column(conn, "revision_plans", "user_id", "INTEGER")
    _add_missing_column(conn, "user_api_keys", "key_suffix", "TEXT DEFAULT ''")
    _add_missing_column(conn, "document_summaries", "provider", "TEXT DEFAULT ''")
    _add_missing_column(conn, "document_summaries", "model", "TEXT DEFAULT ''")
    _add_missing_column(conn, "chat_sessions", "chat_mode", "TEXT DEFAULT 'General Chat'")
    _add_missing_column(conn, "chat_sessions", "context_label", "TEXT DEFAULT ''")
    _add_missing_column(conn, "chat_sessions", "subject_id", "INTEGER")
    _add_missing_column(conn, "chat_sessions", "document_ids_json", "TEXT DEFAULT '[]'")
    _add_missing_column(conn, "chat_sessions", "is_archived", "INTEGER DEFAULT 0")
    _add_missing_column(conn, "chat_messages", "metadata_json", "TEXT DEFAULT '{}'")
    _add_missing_column(conn, "chat_attachments", "warning_message", "TEXT DEFAULT ''")
    _add_missing_column(conn, "study_sessions", "notes", "TEXT DEFAULT ''")

    for table in ["uploaded_documents", "quiz_results", "flashcards", "weak_topics", "revision_plans"]:
        conn.execute(
            f"""
            UPDATE {table}
            SET user_id = (
                SELECT subjects.user_id
                FROM subjects
                WHERE subjects.id = {table}.subject_id
            )
            WHERE user_id IS NULL
            """
        )

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_subjects_user_name
        ON subjects(user_id, name)
        WHERE is_deleted = 0
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON uploaded_documents(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user ON quiz_results(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_user ON flashcards(user_id)")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_weak_topics_user_subject_topic
        ON weak_topics(user_id, subject_id, topic)
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_weak_topics_user ON weak_topics(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_user ON revision_plans(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_api_keys_user ON user_api_keys(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_remember_sessions_hash ON remember_sessions(token_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_summaries_user ON document_summaries(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_archived ON chat_sessions(user_id, is_archived)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_attachments_user ON chat_attachments(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_attachments_session ON chat_attachments(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_attachments_message ON chat_attachments(message_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_user ON user_memories(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_active ON user_memories(user_id, is_active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_study_sessions_user ON study_sessions(user_id)")
    conn.commit()


def _table_references_subjects_old(conn, table_name):
    """Return True when an old migration left a broken subjects_old FK."""
    rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    return any(row["table"] == "subjects_old" for row in rows)


def _rebuild_table(conn, table_name, create_sql, columns, insert_or_ignore=False):
    """Rebuild a table while preserving common columns from the old version."""
    old_table = f"{table_name}_broken_fk"
    old_columns = [
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]
    insert_columns = [column for column in columns if column in old_columns]
    if not insert_columns:
        return

    conn.execute(f"ALTER TABLE {table_name} RENAME TO {old_table}")
    conn.execute(create_sql)
    insert_mode = "INSERT OR IGNORE" if insert_or_ignore else "INSERT"
    column_csv = ", ".join(insert_columns)
    conn.execute(
        f"""
        {insert_mode} INTO {table_name} ({column_csv})
        SELECT {column_csv}
        FROM {old_table}
        """
    )
    conn.execute(f"DROP TABLE {old_table}")


def _repair_subject_foreign_keys(conn):
    """Repair older databases whose child tables still reference subjects_old."""
    tables = [
        "uploaded_documents",
        "quiz_results",
        "flashcards",
        "weak_topics",
        "revision_plans",
    ]
    if not any(_table_references_subjects_old(conn, table) for table in tables):
        return

    conn.execute("PRAGMA foreign_keys = OFF")

    if _table_references_subjects_old(conn, "uploaded_documents"):
        _rebuild_table(
            conn,
            "uploaded_documents",
            """
            CREATE TABLE uploaded_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT DEFAULT 'PDF',
                extracted_text_path TEXT DEFAULT '',
                chunk_count INTEGER DEFAULT 0,
                extraction_method TEXT DEFAULT '',
                extraction_status TEXT DEFAULT '',
                warning_message TEXT DEFAULT '',
                page_count INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """,
            [
                "id",
                "user_id",
                "subject_id",
                "file_name",
                "file_path",
                "file_type",
                "extracted_text_path",
                "chunk_count",
                "extraction_method",
                "extraction_status",
                "warning_message",
                "page_count",
                "description",
                "uploaded_at",
                "is_deleted",
            ],
        )

    if _table_references_subjects_old(conn, "quiz_results"):
        _rebuild_table(
            conn,
            "quiz_results",
            """
            CREATE TABLE quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                topic TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """,
            ["id", "user_id", "subject_id", "score", "total_questions", "topic", "created_at"],
        )

    if _table_references_subjects_old(conn, "flashcards"):
        _rebuild_table(
            conn,
            "flashcards",
            """
            CREATE TABLE flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                topic TEXT DEFAULT '',
                status TEXT DEFAULT 'New',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """,
            ["id", "user_id", "subject_id", "question", "answer", "topic", "status", "created_at"],
        )

    if _table_references_subjects_old(conn, "weak_topics"):
        _rebuild_table(
            conn,
            "weak_topics",
            """
            CREATE TABLE weak_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                weakness_score INTEGER DEFAULT 1,
                notes TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, subject_id, topic),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """,
            ["id", "user_id", "subject_id", "topic", "weakness_score", "notes", "updated_at"],
            insert_or_ignore=True,
        )

    if _table_references_subjects_old(conn, "revision_plans"):
        _rebuild_table(
            conn,
            "revision_plans",
            """
            CREATE TABLE revision_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER NOT NULL,
                exam_date TEXT NOT NULL,
                preparation_level INTEGER NOT NULL,
                confidence_level INTEGER NOT NULL,
                weak_topics TEXT DEFAULT '',
                plan_text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """,
            [
                "id",
                "user_id",
                "subject_id",
                "exam_date",
                "preparation_level",
                "confidence_level",
                "weak_topics",
                "plan_text",
                "created_at",
            ],
        )

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON uploaded_documents(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user ON quiz_results(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_user ON flashcards(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_weak_topics_user ON weak_topics(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_user ON revision_plans(user_id)")
    conn.commit()


def init_db():
    """Compatibility name used by the Streamlit pages."""
    create_tables()


def create_user(name, email, password_hash, auth_provider="email", role="student", is_active=1):
    """Create a user account. Returns the id or None if the email is taken."""
    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, auth_provider, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, email, password_hash, auth_provider, role, int(is_active)),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email):
    """Return one user by normalized email."""
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()


def verify_user_login(email, password, verify_password_callback):
    """Return the user when an email/password pair is valid."""
    clean_email = (email or "").strip().lower()
    if not clean_email or not password:
        return None

    user = get_user_by_email(clean_email)
    if not user:
        return None

    if int(user["is_active"] if "is_active" in user.keys() else 1) != 1:
        return None

    if verify_password_callback(password, user["password_hash"]):
        return user
    return None


def get_or_create_oauth_user(email, full_name, provider="google"):
    """Return an OAuth user by email, creating one when needed."""
    clean_email = (email or "").strip().lower()
    clean_name = (full_name or "").strip() or clean_email.split("@")[0]
    clean_provider = (provider or "google").strip().lower()
    if not clean_email:
        return None

    existing_user = get_user_by_email(clean_email)
    if existing_user:
        if int(existing_user["is_active"] if "is_active" in existing_user.keys() else 1) != 1:
            return None
        return existing_user

    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, auth_provider, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (clean_name[:80], clean_email, "", clean_provider, "student", 1),
        )
        conn.commit()
        return conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()


def get_user_by_id(user_id):
    """Return one user by id."""
    if not user_id:
        return None
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


BRANDING_DEFAULTS = {
    "app_name": "StudyMate AI",
    "app_subtitle": "AI Study Assistant",
    "product_tagline": "Learn smarter. Revise faster. Prepare better.",
    "creator_name": "Ali Shair",
    "creator_role": "CS Student • Developer • Content Creator",
    "creator_description": "I build practical tools using coding and AI to solve real problems for students and small businesses.",
    "creator_email": "infoali014@gmail.com",
    "github_link": "Add your GitHub link here",
    "portfolio_link": "Coming soon",
    "linkedin_link": "Coming soon",
    "instagram_link": "Coming soon",
    "app_version": "v1.0 Beta",
    "footer_text": "StudyMate AI © 2026 • Built by Ali Shair",
    "about_what": "StudyMate AI is a personal study workspace that helps students organize notes, chat with uploaded material, generate quizzes, review flashcards, and plan revision.",
    "about_why": "I built it to make exam preparation more organized, practical, and accessible using AI.",
    "mission_statement": "Help students learn smarter with secure, personalized, and useful AI study tools.",
    "feature_highlights": "Study Library\nChat With Notes\nTeach Me Mode\nQuiz Generator\nFlashcards\nRevision Planner\nMulti-format notes support\nPersonalized user accounts",
    "announcement_active": "false",
    "announcement_type": "info",
    "announcement_message": "",
    "enable_public_signup": "true",
    "enable_demo_mode": "true",
    "enable_google_login": "false",
}


def get_app_setting(key, default=None):
    """Return one application setting."""
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row:
        return row["value"]
    return BRANDING_DEFAULTS.get(key, default)


def set_app_setting(key, value):
    """Save one application setting."""
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key)
            DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value)),
        )
        conn.commit()
    return True


def get_branding_settings():
    """Return all branding settings with defaults filled in."""
    settings = dict(BRANDING_DEFAULTS)
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    for row in rows:
        if row["key"] in settings:
            settings[row["key"]] = row["value"]
    return settings


def save_branding_settings(settings_dict):
    """Save branding/admin-editable settings."""
    for key, value in settings_dict.items():
        if key in BRANDING_DEFAULTS:
            set_app_setting(key, value)
    return True


def reset_branding_settings_to_defaults():
    """Reset branding settings to defaults."""
    with closing(get_connection()) as conn:
        conn.executemany(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key)
            DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            list(BRANDING_DEFAULTS.items()),
        )
        conn.commit()
    return True


def ensure_admin_user(password_hash_callback):
    """Create or update the initial admin from env/secrets when configured."""
    admin_email = (
        os.getenv("ADMIN_EMAIL", "").strip().lower()
        or _get_streamlit_secret("ADMIN_EMAIL").strip().lower()
    )
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip() or _get_streamlit_secret("ADMIN_PASSWORD").strip()
    admin_name = os.getenv("ADMIN_NAME", "").strip() or _get_streamlit_secret("ADMIN_NAME").strip() or "Admin User"
    if not admin_email or not admin_password:
        return None

    existing_user = get_user_by_email(admin_email)
    password_hash = password_hash_callback(admin_password)
    with closing(get_connection()) as conn:
        if existing_user:
            conn.execute(
                """
                UPDATE users
                SET role = 'admin', is_active = 1, name = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (admin_name, password_hash, existing_user["id"]),
            )
            conn.commit()
            return existing_user["id"]

        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, auth_provider, role, is_active)
            VALUES (?, ?, ?, 'email', 'admin', 1)
            """,
            (admin_name, admin_email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid


def user_is_admin(user_id):
    """Return True when the user has admin role."""
    user = get_user_by_id(user_id)
    return bool(user and user["role"] == "admin" and int(user["is_active"]) == 1)


def count_admins():
    """Return number of active admin users."""
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
        ).fetchone()[0]


def get_admin_overview_counts():
    """Return app-wide admin dashboard counts."""
    with closing(get_connection()) as conn:
        return {
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "subjects": conn.execute("SELECT COUNT(*) FROM subjects WHERE is_deleted = 0").fetchone()[0],
            "documents": conn.execute("SELECT COUNT(*) FROM uploaded_documents WHERE is_deleted = 0").fetchone()[0],
            "flashcards": conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0],
            "quizzes": conn.execute("SELECT COUNT(*) FROM quiz_results").fetchone()[0],
            "revision_plans": conn.execute("SELECT COUNT(*) FROM revision_plans").fetchone()[0],
        }


def get_recent_users(limit=8):
    """Return recent users without sensitive fields."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT id, name, email, role, is_active, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()


def get_recent_uploads(limit=8):
    """Return recent uploaded documents for admin overview."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT uploaded_documents.file_name, uploaded_documents.file_type,
                   uploaded_documents.uploaded_at, users.email, subjects.name AS subject_name
            FROM uploaded_documents
            JOIN users ON users.id = uploaded_documents.user_id
            JOIN subjects ON subjects.id = uploaded_documents.subject_id
            WHERE uploaded_documents.is_deleted = 0
            ORDER BY uploaded_documents.uploaded_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()


def get_all_users_with_stats(search_text=""):
    """Return users and basic activity stats for admin management."""
    query = """
        SELECT users.id, users.name, users.email, users.role, users.is_active, users.created_at,
               COUNT(DISTINCT subjects.id) AS subject_count,
               COUNT(DISTINCT uploaded_documents.id) AS document_count
        FROM users
        LEFT JOIN subjects ON subjects.user_id = users.id AND subjects.is_deleted = 0
        LEFT JOIN uploaded_documents ON uploaded_documents.user_id = users.id AND uploaded_documents.is_deleted = 0
    """
    params = []
    clean_search = (search_text or "").strip().lower()
    if clean_search:
        query += " WHERE lower(users.name) LIKE ? OR lower(users.email) LIKE ?"
        params.extend([f"%{clean_search}%", f"%{clean_search}%"])
    query += " GROUP BY users.id ORDER BY users.created_at DESC"
    with closing(get_connection()) as conn:
        return conn.execute(query, params).fetchall()


def update_user_role(target_user_id, role, admin_user_id):
    """Update a user's role, preventing removal of the last admin."""
    if not user_is_admin(admin_user_id):
        return False, "Access denied."
    clean_role = role if role in {"student", "admin"} else "student"
    target = get_user_by_id(target_user_id)
    if not target:
        return False, "User not found."
    if target["role"] == "admin" and clean_role != "admin" and count_admins() <= 1:
        return False, "Cannot remove the last admin."
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (clean_role, target_user_id),
        )
        conn.commit()
    return True, "User role updated."


def set_user_active(target_user_id, is_active, admin_user_id):
    """Enable or disable a user, preventing disabling the last admin."""
    if not user_is_admin(admin_user_id):
        return False, "Access denied."
    target = get_user_by_id(target_user_id)
    if not target:
        return False, "User not found."
    if target["role"] == "admin" and int(is_active) != 1 and count_admins() <= 1:
        return False, "Cannot disable the last admin."
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(is_active), target_user_id),
        )
        conn.commit()
    return True, "User status updated."


def _get_streamlit_secret(name):
    """Read a Streamlit secret without failing in CLI tests."""
    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        if value:
            return str(value)

        # Streamlit secrets use TOML sections. If ADMIN_* keys are pasted after
        # [auth], they become auth.ADMIN_* instead of top-level ADMIN_*.
        # Support that common setup mistake without exposing or logging secrets.
        auth_section = st.secrets.get("auth", {})
        if hasattr(auth_section, "get"):
            return str(auth_section.get(name, ""))
        return ""
    except Exception:
        return ""


def get_encryption_key():
    """
    Return a Fernet-compatible encryption key.

    APP_ENCRYPTION_KEY can be either a Fernet key or any long random secret. If
    it is a normal secret string, we derive a Fernet key with SHA-256 so users do
    not need to understand Fernet formatting.
    """
    raw_key = (
        os.getenv("APP_ENCRYPTION_KEY", "").strip()
        or _get_streamlit_secret("APP_ENCRYPTION_KEY").strip()
    )
    if not raw_key:
        DATA_DIR.mkdir(exist_ok=True)
        if LOCAL_SECRET_PATH.exists():
            raw_key = LOCAL_SECRET_PATH.read_text(encoding="utf-8").strip()
        else:
            raw_key = secrets.token_urlsafe(48)
            LOCAL_SECRET_PATH.write_text(raw_key, encoding="utf-8")

    try:
        from cryptography.fernet import Fernet

        Fernet(raw_key.encode("utf-8"))
        return raw_key.encode("utf-8")
    except Exception:
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


def api_key_saving_configured():
    """Return True when encrypted API key persistence can be used."""
    if get_encryption_key() is None:
        return False
    try:
        import cryptography  # noqa: F401
    except Exception:
        return False
    return True


def encrypt_secret(value):
    """Encrypt a secret value with APP_ENCRYPTION_KEY."""
    key = get_encryption_key()
    if not key:
        raise RuntimeError("APP_ENCRYPTION_KEY is not configured.")
    from cryptography.fernet import Fernet

    return Fernet(key).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value):
    """Decrypt a secret value, returning an empty string if it cannot be read."""
    key = get_encryption_key()
    if not key or not value:
        return ""
    try:
        from cryptography.fernet import Fernet, InvalidToken

        return Fernet(key).decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def save_user_api_key(user_id, provider, api_key):
    """Save one encrypted provider API key for the current user."""
    clean_provider = (provider or "").strip().lower()
    clean_key = (api_key or "").strip()
    if not user_id or not clean_provider or not clean_key:
        return False

    encrypted_key = encrypt_secret(clean_key)
    key_suffix = clean_key[-4:] if len(clean_key) >= 4 else ""
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO user_api_keys (user_id, provider, encrypted_api_key, key_suffix)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, provider)
            DO UPDATE SET
                encrypted_api_key = excluded.encrypted_api_key,
                key_suffix = excluded.key_suffix,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, clean_provider, encrypted_key, key_suffix),
        )
        conn.commit()
    return True


def get_user_api_key(user_id, provider):
    """Return the decrypted API key for this user/provider only."""
    clean_provider = (provider or "").strip().lower()
    if not user_id or not clean_provider or not api_key_saving_configured():
        return ""
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT encrypted_api_key
            FROM user_api_keys
            WHERE user_id = ? AND provider = ?
            """,
            (user_id, clean_provider),
        ).fetchone()
    if not row:
        return ""
    return decrypt_secret(row["encrypted_api_key"])


def get_user_api_key_status(user_id, provider):
    """Return safe metadata about a saved key without exposing the key."""
    clean_provider = (provider or "").strip().lower()
    if not user_id or not clean_provider:
        return None
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT provider, key_suffix, created_at, updated_at
            FROM user_api_keys
            WHERE user_id = ? AND provider = ?
            """,
            (user_id, clean_provider),
        ).fetchone()


def has_user_api_key(user_id, provider):
    """Return True when a user has a saved key record for this provider."""
    return get_user_api_key_status(user_id, provider) is not None


def delete_user_api_key(user_id, provider):
    """Delete only the current user's saved provider key."""
    clean_provider = (provider or "").strip().lower()
    if not user_id or not clean_provider:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "DELETE FROM user_api_keys WHERE user_id = ? AND provider = ?",
            (user_id, clean_provider),
        )
        conn.commit()
        return cursor.rowcount > 0


def _hash_token(token):
    """Return a one-way hash for persistent login tokens."""
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def create_remember_session(user_id, days=30):
    """Create a persistent login token for one user."""
    if not user_id:
        return ""
    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat(timespec="seconds")
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO remember_sessions (user_id, token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (user_id, token_hash, expires_at),
        )
        conn.commit()
    return token


def get_user_by_remember_token(token):
    """Return a user for a valid persistent login token."""
    if not token:
        return None
    now = datetime.utcnow().isoformat(timespec="seconds")
    token_hash = _hash_token(token)
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT users.*
            FROM remember_sessions
            JOIN users ON users.id = remember_sessions.user_id
            WHERE remember_sessions.token_hash = ?
              AND remember_sessions.expires_at > ?
              AND users.is_active = 1
            """,
            (token_hash, now),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE remember_sessions SET last_used_at = CURRENT_TIMESTAMP WHERE token_hash = ?",
                (token_hash,),
            )
            conn.commit()
        return row


def delete_remember_session(token):
    """Delete a persistent login token."""
    if not token:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "DELETE FROM remember_sessions WHERE token_hash = ?",
            (_hash_token(token),),
        )
        conn.commit()
        return cursor.rowcount > 0


def subject_belongs_to_user(subject_id, user_id):
    """Check subject ownership before sensitive actions."""
    if not user_id:
        return False
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT id FROM subjects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
            """,
            (subject_id, user_id),
        ).fetchone()
        return row is not None


def document_belongs_to_user(document_id, user_id):
    """Check document ownership before preview/chat/delete actions."""
    if not user_id:
        return False
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT uploaded_documents.id
            FROM uploaded_documents
            JOIN subjects ON subjects.id = uploaded_documents.subject_id
            WHERE uploaded_documents.id = ?
              AND uploaded_documents.user_id = ?
              AND subjects.user_id = ?
              AND uploaded_documents.is_deleted = 0
              AND subjects.is_deleted = 0
            """,
            (document_id, user_id, user_id),
        ).fetchone()
        return row is not None


def add_subject(name, description="", user_id=None):
    """Add a subject for the current user and return its new id."""
    if not user_id:
        return None
    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO subjects (user_id, name, description)
                VALUES (?, ?, ?)
                """,
                (user_id, name.strip(), description.strip()),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def create_subject(name, description="", user_id=None):
    """Compatibility helper for the dashboard page."""
    return add_subject(name, description, user_id=user_id) is not None


def get_subjects(user_id=None):
    """Return the current user's subjects sorted by newest first."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT * FROM subjects
            WHERE user_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()


def get_subject(subject_id, user_id=None):
    """Return one subject only if it belongs to the current user."""
    if not user_id:
        return None
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT * FROM subjects
            WHERE id = ? AND user_id = ? AND is_deleted = 0
            """,
            (subject_id, user_id),
        ).fetchone()


def _delete_file_if_inside_user_data(file_path, user_id):
    """Delete stored app files only when they live inside this user's data folder."""
    if not file_path or not user_id:
        return
    path = Path(file_path)
    user_upload_root = DATA_DIR / "uploads" / str(user_id)
    user_text_root = DATA_DIR / "extracted_text" / str(user_id)

    try:
        resolved_path = path.resolve()
    except OSError:
        return

    allowed = is_path_inside(user_upload_root, resolved_path) or is_path_inside(
        user_text_root, resolved_path
    )
    if allowed and resolved_path.is_file():
        try:
            resolved_path.unlink(missing_ok=True)
        except OSError:
            # File cleanup should not block deleting the database record.
            return


def delete_subject(subject_id, user_id=None):
    """Delete one subject and related records only for the current user."""
    if not subject_belongs_to_user(subject_id, user_id):
        return False
    with closing(get_connection()) as conn:
        documents = conn.execute(
            """
            SELECT file_path, extracted_text_path
            FROM uploaded_documents
            WHERE subject_id = ? AND user_id = ? AND is_deleted = 0
            """,
            (subject_id, user_id),
        ).fetchall()

        for document in documents:
            _delete_file_if_inside_user_data(document["file_path"], user_id)
            _delete_file_if_inside_user_data(document["extracted_text_path"], user_id)

        conn.execute("DELETE FROM uploaded_documents WHERE subject_id = ? AND user_id = ?", (subject_id, user_id))
        conn.execute("DELETE FROM quiz_results WHERE subject_id = ? AND user_id = ?", (subject_id, user_id))
        conn.execute("DELETE FROM flashcards WHERE subject_id = ? AND user_id = ?", (subject_id, user_id))
        conn.execute("DELETE FROM weak_topics WHERE subject_id = ? AND user_id = ?", (subject_id, user_id))
        conn.execute("DELETE FROM revision_plans WHERE subject_id = ? AND user_id = ?", (subject_id, user_id))
        conn.execute("DELETE FROM document_summaries WHERE subject_id = ? AND user_id = ?", (subject_id, user_id))
        conn.execute("DELETE FROM subjects WHERE id = ? AND user_id = ?", (subject_id, user_id))
        conn.commit()
        return True


def save_uploaded_document_metadata(
    subject_id,
    file_name,
    file_path,
    chunk_count=0,
    extracted_text_path="",
    file_type="PDF",
    description="",
    extraction_method="",
    extraction_status="",
    warning_message="",
    page_count=0,
    user_id=None,
):
    """Save metadata for an uploaded document and return the document id."""
    if not subject_belongs_to_user(subject_id, user_id):
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO uploaded_documents
                (
                    user_id, subject_id, file_name, file_path, file_type,
                    extracted_text_path, chunk_count, extraction_method,
                    extraction_status, warning_message, page_count, description
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                subject_id,
                file_name,
                file_path,
                file_type.upper(),
                extracted_text_path,
                chunk_count,
                extraction_method,
                extraction_status,
                warning_message,
                int(page_count or 0),
                description.strip(),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def add_document(subject_id, file_name, file_path, chunk_count, user_id=None):
    """Compatibility helper for the upload page."""
    return save_uploaded_document_metadata(
        subject_id=subject_id,
        file_name=file_name,
        file_path=file_path,
        chunk_count=chunk_count,
        user_id=user_id,
    )


def get_documents(subject_id=None, user_id=None):
    """Return current-user uploaded documents, optionally filtered by subject."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        params = [user_id, user_id]
        where = """
            uploaded_documents.user_id = ?
            AND subjects.user_id = ?
            AND uploaded_documents.is_deleted = 0
            AND subjects.is_deleted = 0
        """
        if subject_id:
            where += " AND uploaded_documents.subject_id = ?"
            params.append(subject_id)

        return conn.execute(
            f"""
            SELECT uploaded_documents.*, subjects.name AS subject_name
            FROM uploaded_documents
            JOIN subjects ON subjects.id = uploaded_documents.subject_id
            WHERE {where}
            ORDER BY uploaded_documents.uploaded_at DESC
            """,
            params,
        ).fetchall()


def get_documents_by_subject(subject_id, user_id=None):
    """Return all uploaded documents for one owned subject."""
    if not subject_belongs_to_user(subject_id, user_id):
        return []
    return get_documents(subject_id=subject_id, user_id=user_id)


def get_all_documents(user_id=None):
    """Return all current-user uploaded documents with their subject names."""
    return get_documents(user_id=user_id)


def get_document_by_id(document_id, user_id=None):
    """Return one uploaded document only if it belongs to the current user."""
    if not user_id:
        return None
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT uploaded_documents.*, subjects.name AS subject_name
            FROM uploaded_documents
            JOIN subjects ON subjects.id = uploaded_documents.subject_id
            WHERE uploaded_documents.id = ?
              AND uploaded_documents.user_id = ?
              AND subjects.user_id = ?
              AND uploaded_documents.is_deleted = 0
              AND subjects.is_deleted = 0
            """,
            (document_id, user_id, user_id),
        ).fetchone()


def delete_document(document_id, user_id=None):
    """Delete one uploaded document only if it belongs to the current user."""
    document = get_document_by_id(document_id, user_id=user_id)
    if not document:
        return False
    with closing(get_connection()) as conn:
        _delete_file_if_inside_user_data(document["file_path"], user_id)
        _delete_file_if_inside_user_data(document["extracted_text_path"], user_id)
        conn.execute(
            "DELETE FROM document_summaries WHERE document_id = ? AND user_id = ?",
            (document_id, user_id),
        )
        conn.execute(
            "DELETE FROM uploaded_documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        )
        conn.commit()
        return True


def get_document_count_by_subject(subject_id, user_id=None):
    """Return the number of uploaded documents for one owned subject."""
    if not subject_belongs_to_user(subject_id, user_id):
        return 0
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT COUNT(*) FROM uploaded_documents
            WHERE subject_id = ? AND user_id = ? AND is_deleted = 0
            """,
            (subject_id, user_id),
        ).fetchone()[0]


def get_subject_document_counts(user_id=None):
    """Return each owned subject with its uploaded document count."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT subjects.*, COUNT(uploaded_documents.id) AS document_count
            FROM subjects
            LEFT JOIN uploaded_documents
                ON uploaded_documents.subject_id = subjects.id
                AND uploaded_documents.user_id = ?
                AND uploaded_documents.is_deleted = 0
            WHERE subjects.user_id = ? AND subjects.is_deleted = 0
            GROUP BY subjects.id
            ORDER BY subjects.created_at DESC
            """,
            (user_id, user_id),
        ).fetchall()


def save_quiz_result(subject_id, score, total_questions, topic="", user_id=None):
    """Save a quiz attempt for the current user and return the result id."""
    if not subject_belongs_to_user(subject_id, user_id):
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO quiz_results (user_id, subject_id, score, total_questions, topic)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, subject_id, score, total_questions, topic.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def get_quiz_results(subject_id=None, user_id=None, limit=50):
    """Return current-user quiz history, newest first."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        params = [user_id, user_id]
        query = """
            SELECT quiz_results.*, subjects.name AS subject_name
            FROM quiz_results
            JOIN subjects ON subjects.id = quiz_results.subject_id
            WHERE quiz_results.user_id = ?
              AND subjects.user_id = ?
              AND subjects.is_deleted = 0
        """
        if subject_id:
            query += " AND quiz_results.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY quiz_results.created_at DESC LIMIT ?"
        params.append(int(limit))
        return conn.execute(query, params).fetchall()


def save_flashcard(subject_id, question, answer, topic="", user_id=None):
    """Save one flashcard for the current user and return its id."""
    if not subject_belongs_to_user(subject_id, user_id):
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO flashcards (user_id, subject_id, question, answer, topic, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, subject_id, question.strip(), answer.strip(), topic.strip(), "New"),
        )
        conn.commit()
        return cursor.lastrowid


def get_flashcards(subject_id=None, topic=None, user_id=None):
    """Return current-user flashcards, optionally filtered by subject and topic."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        query = """
            SELECT flashcards.*
            FROM flashcards
            JOIN subjects ON subjects.id = flashcards.subject_id
            WHERE flashcards.user_id = ?
              AND subjects.user_id = ?
              AND subjects.is_deleted = 0
        """
        params = [user_id, user_id]
        if subject_id:
            query += " AND flashcards.subject_id = ?"
            params.append(subject_id)
        if topic:
            query += " AND flashcards.topic = ?"
            params.append(topic)
        query += " ORDER BY flashcards.created_at DESC, flashcards.id DESC"
        return conn.execute(query, params).fetchall()


def update_flashcard_status(flashcard_id, status, user_id=None):
    """Mark a flashcard as New, Learned, or Weak only for the current user."""
    if not user_id:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "UPDATE flashcards SET status = ? WHERE id = ? AND user_id = ?",
            (status, flashcard_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_flashcards_by_subject(subject_id, user_id=None):
    """Delete all flashcards for one owned subject."""
    if not subject_belongs_to_user(subject_id, user_id):
        return False
    with closing(get_connection()) as conn:
        conn.execute(
            "DELETE FROM flashcards WHERE subject_id = ? AND user_id = ?",
            (subject_id, user_id),
        )
        conn.commit()
        return True


def update_weak_topic(subject_id, topic, weakness_score=1, notes="", user_id=None):
    """Add or update a weak topic for an owned subject."""
    if not subject_belongs_to_user(subject_id, user_id):
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO weak_topics (user_id, subject_id, topic, weakness_score, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, subject_id, topic) DO UPDATE SET
                weakness_score = excluded.weakness_score,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, subject_id, topic.strip(), weakness_score, notes.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def get_weak_topics(subject_id=None, user_id=None):
    """Return current-user weak topics, optionally filtered by subject."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        query = """
            SELECT weak_topics.*, subjects.name AS subject_name
            FROM weak_topics
            JOIN subjects ON subjects.id = weak_topics.subject_id
            WHERE weak_topics.user_id = ?
              AND subjects.user_id = ?
              AND subjects.is_deleted = 0
        """
        params = [user_id, user_id]
        if subject_id:
            query += " AND weak_topics.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY weak_topics.weakness_score DESC, weak_topics.updated_at DESC"
        return conn.execute(query, params).fetchall()


def save_revision_plan(
    subject_id,
    exam_date,
    preparation_level,
    confidence_level,
    weak_topics,
    plan_text,
    user_id=None,
):
    """Save a generated revision plan for the current user and return its id."""
    if not subject_belongs_to_user(subject_id, user_id):
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO revision_plans
                (user_id, subject_id, exam_date, preparation_level, confidence_level, weak_topics, plan_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                subject_id,
                str(exam_date),
                preparation_level,
                confidence_level,
                ", ".join(weak_topics),
                plan_text,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_revision_plans(subject_id=None, user_id=None):
    """Return current-user saved revision plans, newest first."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        query = """
            SELECT revision_plans.*, subjects.name AS subject_name
            FROM revision_plans
            JOIN subjects ON subjects.id = revision_plans.subject_id
            WHERE revision_plans.user_id = ?
              AND subjects.user_id = ?
              AND subjects.is_deleted = 0
        """
        params = [user_id, user_id]
        if subject_id:
            query += " AND revision_plans.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY revision_plans.created_at DESC"
        return conn.execute(query, params).fetchall()


def save_document_summary(document_id, subject_id, summary_text, user_id=None, provider="", model=""):
    """Save or update one document summary for the current user."""
    if not document_belongs_to_user(document_id, user_id):
        return False
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO document_summaries
                (user_id, document_id, subject_id, summary_text, provider, model)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, document_id)
            DO UPDATE SET
                summary_text = excluded.summary_text,
                provider = excluded.provider,
                model = excluded.model,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, document_id, subject_id, summary_text.strip(), provider, model),
        )
        conn.commit()
    return True


def get_document_summary(document_id, user_id=None):
    """Return a saved summary for one owned document."""
    if not document_belongs_to_user(document_id, user_id):
        return None
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT *
            FROM document_summaries
            WHERE document_id = ? AND user_id = ?
            """,
            (document_id, user_id),
        ).fetchone()


def create_chat_session(
    user_id,
    title=None,
    mode="General Chat",
    subject_id=None,
    document_ids=None,
    chat_mode=None,
    context_label="",
):
    """Create a saved AI chat session for one user."""
    if not user_id:
        return None
    clean_title = (title or "New Chat").strip()[:80] or "New Chat"
    clean_mode = chat_mode or mode or "General Chat"
    document_ids_json = json.dumps(document_ids or [])
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO chat_sessions
                (user_id, title, chat_mode, subject_id, document_ids_json, context_label)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, clean_title, clean_mode, subject_id, document_ids_json, context_label),
        )
        conn.commit()
        return cursor.lastrowid


def get_chat_sessions(user_id, limit=30, include_archived=False, search=""):
    """Return saved chat sessions for a user."""
    if not user_id:
        return []
    clauses = ["user_id = ?"]
    params = [user_id]
    if not include_archived:
        clauses.append("is_archived = 0")
    if search:
        clauses.append("LOWER(title) LIKE ?")
        params.append(f"%{str(search).strip().lower()}%")
    params.append(int(limit))
    with closing(get_connection()) as conn:
        return conn.execute(
            f"""
            SELECT *
            FROM chat_sessions
            WHERE {" AND ".join(clauses)}
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()


def get_chat_session(user_id, session_id):
    """Return one owned chat session."""
    if not user_id or not session_id:
        return None
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT *
            FROM chat_sessions
            WHERE id = ? AND user_id = ? AND is_archived = 0
            """,
            (session_id, user_id),
        ).fetchone()


def update_chat_session_title(user_id, session_id, new_title):
    """Rename one owned chat session."""
    if not user_id or not session_id:
        return False
    clean_title = str(new_title or "").strip()[:80]
    if not clean_title:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND is_archived = 0
            """,
            (clean_title, session_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_chat_session_context(user_id, session_id, mode=None, subject_id="__keep__", document_ids=None, context_label=None):
    """Update mode/context metadata for one owned chat session."""
    if not user_id or not session_id:
        return False
    updates = []
    params = []
    if mode is not None:
        updates.append("chat_mode = ?")
        params.append(mode)
    if subject_id != "__keep__":
        updates.append("subject_id = ?")
        params.append(subject_id)
    if document_ids is not None:
        updates.append("document_ids_json = ?")
        params.append(json.dumps(document_ids or []))
    if context_label is not None:
        updates.append("context_label = ?")
        params.append(context_label)
    if not updates:
        return False
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.extend([session_id, user_id])
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            f"""
            UPDATE chat_sessions
            SET {", ".join(updates)}
            WHERE id = ? AND user_id = ? AND is_archived = 0
            """,
            params,
        )
        conn.commit()
        return cursor.rowcount > 0


def update_chat_session_timestamp(user_id, session_id):
    """Touch one owned chat session timestamp."""
    if not user_id or not session_id:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE chat_sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND is_archived = 0
            """,
            (session_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def archive_chat_session(user_id, session_id):
    """Archive one owned chat session so it disappears from the normal list."""
    if not user_id or not session_id:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE chat_sessions
            SET is_archived = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_chat_messages(user_id, session_id, limit=None):
    """Return saved messages for one owned chat session."""
    if not user_id or not session_id:
        return []
    with closing(get_connection()) as conn:
        if limit:
            return conn.execute(
                """
                SELECT *
                FROM (
                    SELECT chat_messages.*
                    FROM chat_messages
                    JOIN chat_sessions ON chat_sessions.id = chat_messages.session_id
                    WHERE chat_messages.session_id = ?
                      AND chat_messages.user_id = ?
                      AND chat_sessions.user_id = ?
                      AND chat_sessions.is_archived = 0
                    ORDER BY chat_messages.id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (session_id, user_id, user_id, int(limit)),
            ).fetchall()

        sql = """
            SELECT chat_messages.*
            FROM chat_messages
            JOIN chat_sessions ON chat_sessions.id = chat_messages.session_id
            WHERE chat_messages.session_id = ?
              AND chat_messages.user_id = ?
              AND chat_sessions.user_id = ?
              AND chat_sessions.is_archived = 0
            ORDER BY chat_messages.id ASC
            """
        params = [session_id, user_id, user_id]
        return conn.execute(sql, params).fetchall()


def save_chat_message(
    user_id,
    session_id,
    role,
    content,
    metadata=None,
    context_json="{}",
    sources_json="[]",
    warning="",
    source_count=0,
    suggestions_json="[]",
):
    """Save one chat message and update its parent session timestamp."""
    if not session_id or not user_id or role not in {"user", "assistant"}:
        return None
    with closing(get_connection()) as conn:
        owner = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ? AND is_archived = 0",
            (session_id, user_id),
        ).fetchone()
        if not owner:
            return None
        cursor = conn.execute(
            """
            INSERT INTO chat_messages
                (session_id, user_id, role, content, context_json, metadata_json, sources_json, warning, source_count, suggestions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                role,
                content,
                context_json,
                json.dumps(metadata or {}),
                sources_json,
                warning,
                int(source_count or 0),
                suggestions_json,
            ),
        )
        conn.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.commit()
        return cursor.lastrowid


def clear_chat_messages(user_id, session_id):
    """Delete messages from one owned chat session without deleting the session."""
    if not user_id or not session_id:
        return False
    with closing(get_connection()) as conn:
        owner = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ? AND is_archived = 0",
            (session_id, user_id),
        ).fetchone()
        if not owner:
            return False
        conn.execute(
            "DELETE FROM chat_messages WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.commit()
    return True


def clear_chat_session(user_id, session_id):
    """Compatibility wrapper for clearing messages in one owned chat session."""
    return clear_chat_messages(user_id, session_id)


def delete_chat_session(user_id, session_id):
    """Delete one owned chat session and its messages."""
    if not user_id or not session_id:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def save_chat_attachment(
    user_id,
    session_id,
    file_name,
    file_path,
    file_type="",
    mime_type="",
    file_size=0,
    extracted_text="",
    extraction_method="",
    warning_message="",
    message_id=None,
):
    """Save metadata for one chat-scoped attachment."""
    if not user_id or not session_id or not file_name or not file_path:
        return None
    with closing(get_connection()) as conn:
        owner = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ? AND is_archived = 0",
            (session_id, user_id),
        ).fetchone()
        if not owner:
            return None
        cursor = conn.execute(
            """
            INSERT INTO chat_attachments
                (user_id, session_id, message_id, file_name, file_path, file_type,
                 mime_type, file_size, extracted_text, extraction_method, warning_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                session_id,
                message_id,
                file_name,
                file_path,
                file_type,
                mime_type,
                int(file_size or 0),
                extracted_text or "",
                extraction_method or "",
                warning_message or "",
            ),
        )
        conn.commit()
        return cursor.lastrowid


def attach_chat_attachments_to_message(user_id, session_id, attachment_ids, message_id):
    """Link already-saved attachments to one owned chat message."""
    if not user_id or not session_id or not attachment_ids or not message_id:
        return False
    placeholders = ",".join("?" for _ in attachment_ids)
    params = [message_id, *attachment_ids, user_id, session_id]
    with closing(get_connection()) as conn:
        conn.execute(
            f"""
            UPDATE chat_attachments
            SET message_id = ?
            WHERE id IN ({placeholders})
              AND user_id = ?
              AND session_id = ?
            """,
            params,
        )
        conn.commit()
    return True


def get_chat_attachments(user_id, session_id, message_id=None):
    """Return attachments for one owned chat session, optionally one message."""
    if not user_id or not session_id:
        return []
    clauses = [
        "chat_attachments.user_id = ?",
        "chat_attachments.session_id = ?",
        "chat_sessions.user_id = ?",
        "chat_sessions.is_archived = 0",
    ]
    params = [user_id, session_id, user_id]
    if message_id is not None:
        clauses.append("chat_attachments.message_id = ?")
        params.append(message_id)
    with closing(get_connection()) as conn:
        return conn.execute(
            f"""
            SELECT chat_attachments.*
            FROM chat_attachments
            JOIN chat_sessions ON chat_sessions.id = chat_attachments.session_id
            WHERE {" AND ".join(clauses)}
            ORDER BY chat_attachments.id ASC
            """,
            params,
        ).fetchall()


def save_user_memory(user_id, key, value, category="custom"):
    """Save or update one active user memory."""
    if not user_id or not key or not value:
        return None
    clean_key = str(key).strip()[:80]
    clean_value = str(value).strip()[:300]
    clean_category = str(category or "custom").strip()[:60]
    if not clean_key or not clean_value:
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO user_memories (user_id, memory_key, memory_value, category, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(user_id, memory_key)
            DO UPDATE SET
                memory_value = excluded.memory_value,
                category = excluded.category,
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, clean_key, clean_value, clean_category),
        )
        conn.commit()
        return cursor.lastrowid


def get_user_memories(user_id, active_only=True):
    """Return memories for one user only."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        if active_only:
            return conn.execute(
                """
                SELECT *
                FROM user_memories
                WHERE user_id = ? AND is_active = 1
                ORDER BY updated_at DESC, id DESC
                """,
                (user_id,),
            ).fetchall()
        return conn.execute(
            """
            SELECT *
            FROM user_memories
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()


def update_user_memory(user_id, memory_id, value):
    """Update one owned user memory value."""
    if not user_id or not memory_id:
        return False
    clean_value = str(value or "").strip()[:300]
    if not clean_value:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE user_memories
            SET memory_value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (clean_value, memory_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_user_memory(user_id, memory_id):
    """Soft-delete one owned user memory."""
    if not user_id or not memory_id:
        return False
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE user_memories
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (memory_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def clear_user_memories(user_id):
    """Soft-delete all memories for the current user only."""
    if not user_id:
        return False
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE user_memories
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (user_id,),
        )
        conn.commit()
    return True


def save_study_session(user_id, subject_id=None, duration_minutes=25, session_type="Focus", notes=""):
    """Save one completed Pomodoro/study session."""
    if not user_id:
        return None
    if subject_id and not subject_belongs_to_user(subject_id, user_id):
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO study_sessions (user_id, subject_id, duration_minutes, session_type, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, subject_id, int(duration_minutes), session_type, notes.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def get_study_sessions(user_id, limit=20):
    """Return saved Pomodoro/study sessions."""
    if not user_id:
        return []
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT study_sessions.*, subjects.name AS subject_name
            FROM study_sessions
            LEFT JOIN subjects ON subjects.id = study_sessions.subject_id
            WHERE study_sessions.user_id = ?
            ORDER BY study_sessions.completed_at DESC
            LIMIT ?
            """,
            (user_id, int(limit)),
        ).fetchall()


def get_dashboard_counts(user_id=None):
    """Return simple counts for the current user's dashboard cards."""
    if not user_id:
        return {"subjects": 0, "documents": 0, "flashcards": 0, "quizzes": 0}
    with closing(get_connection()) as conn:
        subjects = conn.execute(
            "SELECT COUNT(*) FROM subjects WHERE user_id = ? AND is_deleted = 0",
            (user_id,),
        ).fetchone()[0]
        documents = conn.execute(
            "SELECT COUNT(*) FROM uploaded_documents WHERE user_id = ? AND is_deleted = 0",
            (user_id,),
        ).fetchone()[0]
        flashcards = conn.execute(
            "SELECT COUNT(*) FROM flashcards WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        quizzes = conn.execute(
            "SELECT COUNT(*) FROM quiz_results WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        return {
            "subjects": subjects,
            "documents": documents,
            "flashcards": flashcards,
            "quizzes": quizzes,
        }
