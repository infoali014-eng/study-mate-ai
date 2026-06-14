import sqlite3
from contextlib import closing
from pathlib import Path

from modules.security import is_path_inside


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "studymate.db"


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
        conn.commit()

        _add_missing_column(conn, "subjects", "user_id", "INTEGER")
        _add_missing_column(conn, "subjects", "is_deleted", "INTEGER DEFAULT 0")
        _ensure_subjects_table_allows_per_user_names(conn)
        _run_migrations(conn)


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
    _add_missing_column(conn, "users", "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
    _add_missing_column(conn, "subjects", "user_id", "INTEGER")
    _add_missing_column(conn, "subjects", "is_deleted", "INTEGER DEFAULT 0")
    _add_missing_column(conn, "uploaded_documents", "user_id", "INTEGER")
    _add_missing_column(conn, "uploaded_documents", "file_type", "TEXT DEFAULT 'PDF'")
    _add_missing_column(conn, "uploaded_documents", "description", "TEXT DEFAULT ''")
    _add_missing_column(conn, "uploaded_documents", "is_deleted", "INTEGER DEFAULT 0")
    _add_missing_column(conn, "quiz_results", "user_id", "INTEGER")
    _add_missing_column(conn, "flashcards", "user_id", "INTEGER")
    _add_missing_column(conn, "flashcards", "status", "TEXT DEFAULT 'New'")
    _add_missing_column(conn, "weak_topics", "user_id", "INTEGER")
    _add_missing_column(conn, "revision_plans", "user_id", "INTEGER")

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
    conn.commit()


def init_db():
    """Compatibility name used by the Streamlit pages."""
    create_tables()


def create_user(name, email, password_hash):
    """Create a user account. Returns the id or None if the email is taken."""
    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (name, email, password_hash),
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


def get_user_by_id(user_id):
    """Return one user by id."""
    if not user_id:
        return None
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


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
        resolved_path.unlink(missing_ok=True)


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
    user_id=None,
):
    """Save metadata for an uploaded document and return the document id."""
    if not subject_belongs_to_user(subject_id, user_id):
        return None
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO uploaded_documents
                (user_id, subject_id, file_name, file_path, file_type, extracted_text_path, chunk_count, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                subject_id,
                file_name,
                file_path,
                file_type.upper(),
                extracted_text_path,
                chunk_count,
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
