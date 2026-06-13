import sqlite3
from contextlib import closing
from pathlib import Path


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
    """Create all StudyMate AI tables if they do not already exist."""
    with closing(get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                study_goal TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploaded_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT DEFAULT 'PDF',
                extracted_text_path TEXT DEFAULT '',
                chunk_count INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                topic TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                topic TEXT DEFAULT '',
                status TEXT DEFAULT 'New',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weak_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                weakness_score INTEGER DEFAULT 1,
                notes TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (subject_id, topic),
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS revision_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                exam_date TEXT NOT NULL,
                preparation_level INTEGER NOT NULL,
                confidence_level INTEGER NOT NULL,
                weak_topics TEXT DEFAULT '',
                plan_text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
        _add_missing_column(conn, "flashcards", "status", "TEXT DEFAULT 'New'")
        _add_missing_column(conn, "uploaded_documents", "file_type", "TEXT DEFAULT 'PDF'")
        _add_missing_column(conn, "uploaded_documents", "description", "TEXT DEFAULT ''")


def _add_missing_column(conn, table_name, column_name, column_definition):
    """Add a column when an older local database was created before it existed."""
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    column_names = [column["name"] for column in columns]

    if column_name not in column_names:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
        conn.commit()


def init_db():
    """Compatibility name used by the Streamlit pages."""
    create_tables()


def add_subject(name, description="", user_id=None):
    """Add a subject and return its new id. Return None if the name already exists."""
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


def create_subject(name, description=""):
    """Compatibility helper for the dashboard page."""
    return add_subject(name, description) is not None


def get_subjects():
    """Return all subjects sorted by newest first."""
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT * FROM subjects ORDER BY created_at DESC"
        ).fetchall()


def get_subject(subject_id):
    """Return one subject by id."""
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT * FROM subjects WHERE id = ?", (subject_id,)
        ).fetchone()


def _delete_file_if_inside_data(file_path):
    """Delete one stored app file only when it lives inside the local data folder."""
    if not file_path:
        return

    path = Path(file_path)
    try:
        resolved_path = path.resolve()
        resolved_data_dir = DATA_DIR.resolve()
    except OSError:
        return

    # This protects other folders from accidental deletion.
    if resolved_data_dir in resolved_path.parents and resolved_path.is_file():
        resolved_path.unlink(missing_ok=True)


def delete_subject(subject_id):
    """
    Delete one subject and its related local SQLite data.

    Related uploaded document files are removed only when their saved paths are
    inside the app's data folder. Other subjects are not touched.
    """
    with closing(get_connection()) as conn:
        subject = conn.execute(
            "SELECT * FROM subjects WHERE id = ?", (subject_id,)
        ).fetchone()

        if not subject:
            return False

        documents = conn.execute(
            """
            SELECT file_path, extracted_text_path
            FROM uploaded_documents
            WHERE subject_id = ?
            """,
            (subject_id,),
        ).fetchall()

        for document in documents:
            _delete_file_if_inside_data(document["file_path"])
            _delete_file_if_inside_data(document["extracted_text_path"])

        # Explicit deletes make the cleanup clear for beginners and also work
        # even if an older database was created without foreign-key cascades.
        conn.execute("DELETE FROM uploaded_documents WHERE subject_id = ?", (subject_id,))
        conn.execute("DELETE FROM quiz_results WHERE subject_id = ?", (subject_id,))
        conn.execute("DELETE FROM flashcards WHERE subject_id = ?", (subject_id,))
        conn.execute("DELETE FROM weak_topics WHERE subject_id = ?", (subject_id,))
        conn.execute("DELETE FROM revision_plans WHERE subject_id = ?", (subject_id,))
        conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
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
):
    """Save metadata for an uploaded PDF and return the document id."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO uploaded_documents
                (subject_id, file_name, file_path, file_type, extracted_text_path, chunk_count, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
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


def add_document(subject_id, file_name, file_path, chunk_count):
    """Compatibility helper for the upload page."""
    return save_uploaded_document_metadata(
        subject_id=subject_id,
        file_name=file_name,
        file_path=file_path,
        chunk_count=chunk_count,
    )


def get_documents(subject_id=None):
    """Return uploaded documents, optionally filtered by subject."""
    with closing(get_connection()) as conn:
        if subject_id:
            return conn.execute(
                """
                SELECT uploaded_documents.*, subjects.name AS subject_name
                FROM uploaded_documents
                JOIN subjects ON subjects.id = uploaded_documents.subject_id
                WHERE subject_id = ?
                ORDER BY uploaded_documents.uploaded_at DESC
                """,
                (subject_id,),
            ).fetchall()

        return conn.execute(
            """
            SELECT uploaded_documents.*, subjects.name AS subject_name
            FROM uploaded_documents
            JOIN subjects ON subjects.id = uploaded_documents.subject_id
            ORDER BY uploaded_documents.uploaded_at DESC
            """
        ).fetchall()


def get_documents_by_subject(subject_id):
    """Return all uploaded documents for one subject."""
    return get_documents(subject_id=subject_id)


def get_all_documents():
    """Return all uploaded documents with their subject names."""
    return get_documents()


def get_document_by_id(document_id):
    """Return one uploaded document by id."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT uploaded_documents.*, subjects.name AS subject_name
            FROM uploaded_documents
            JOIN subjects ON subjects.id = uploaded_documents.subject_id
            WHERE uploaded_documents.id = ?
            """,
            (document_id,),
        ).fetchone()


def delete_document(document_id):
    """
    Delete one uploaded document and its local extracted/uploaded files.

    This does not touch other documents, subjects, quiz results, flashcards, or
    revision plans.
    """
    with closing(get_connection()) as conn:
        document = conn.execute(
            "SELECT * FROM uploaded_documents WHERE id = ?",
            (document_id,),
        ).fetchone()

        if not document:
            return False

        _delete_file_if_inside_data(document["file_path"])
        _delete_file_if_inside_data(document["extracted_text_path"])
        conn.execute("DELETE FROM uploaded_documents WHERE id = ?", (document_id,))
        conn.commit()
        return True


def get_document_count_by_subject(subject_id):
    """Return the number of uploaded documents for one subject."""
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM uploaded_documents WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()[0]


def get_subject_document_counts():
    """Return every subject with its uploaded document count."""
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT subjects.*, COUNT(uploaded_documents.id) AS document_count
            FROM subjects
            LEFT JOIN uploaded_documents
                ON uploaded_documents.subject_id = subjects.id
            GROUP BY subjects.id
            ORDER BY subjects.created_at DESC
            """
        ).fetchall()


def save_quiz_result(subject_id, score, total_questions, topic=""):
    """Save a quiz attempt and return the result id."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO quiz_results (subject_id, score, total_questions, topic)
            VALUES (?, ?, ?, ?)
            """,
            (subject_id, score, total_questions, topic.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def save_flashcard(subject_id, question, answer, topic=""):
    """Save one flashcard and return its id."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO flashcards (subject_id, question, answer, topic, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subject_id, question.strip(), answer.strip(), topic.strip(), "New"),
        )
        conn.commit()
        return cursor.lastrowid


def get_flashcards(subject_id=None, topic=None):
    """Return saved flashcards, optionally filtered by subject and topic."""
    with closing(get_connection()) as conn:
        query = "SELECT * FROM flashcards WHERE 1 = 1"
        params = []

        if subject_id:
            query += " AND subject_id = ?"
            params.append(subject_id)

        if topic:
            query += " AND topic = ?"
            params.append(topic)

        query += " ORDER BY created_at DESC, id DESC"
        return conn.execute(query, params).fetchall()


def update_flashcard_status(flashcard_id, status):
    """Mark a flashcard as New, Learned, or Weak."""
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE flashcards SET status = ? WHERE id = ?",
            (status, flashcard_id),
        )
        conn.commit()


def update_weak_topic(subject_id, topic, weakness_score=1, notes=""):
    """
    Add or update a weak topic for a subject.

    If the topic already exists for the subject, its score, notes, and update
    time are refreshed instead of creating a duplicate row.
    """
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO weak_topics (subject_id, topic, weakness_score, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(subject_id, topic) DO UPDATE SET
                weakness_score = excluded.weakness_score,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (subject_id, topic.strip(), weakness_score, notes.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def get_weak_topics(subject_id=None):
    """Return weak topics, optionally filtered by subject."""
    with closing(get_connection()) as conn:
        if subject_id:
            return conn.execute(
                """
                SELECT * FROM weak_topics
                WHERE subject_id = ?
                ORDER BY weakness_score DESC, updated_at DESC
                """,
                (subject_id,),
            ).fetchall()

        return conn.execute(
            """
            SELECT weak_topics.*, subjects.name AS subject_name
            FROM weak_topics
            JOIN subjects ON subjects.id = weak_topics.subject_id
            ORDER BY weakness_score DESC, updated_at DESC
            """
        ).fetchall()


def save_revision_plan(
    subject_id,
    exam_date,
    preparation_level,
    confidence_level,
    weak_topics,
    plan_text,
):
    """Save a generated revision plan locally in SQLite and return its id."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO revision_plans
                (subject_id, exam_date, preparation_level, confidence_level, weak_topics, plan_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
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


def get_revision_plans(subject_id=None):
    """Return saved revision plans, newest first."""
    with closing(get_connection()) as conn:
        if subject_id:
            return conn.execute(
                """
                SELECT revision_plans.*, subjects.name AS subject_name
                FROM revision_plans
                JOIN subjects ON subjects.id = revision_plans.subject_id
                WHERE subject_id = ?
                ORDER BY revision_plans.created_at DESC
                """,
                (subject_id,),
            ).fetchall()

        return conn.execute(
            """
            SELECT revision_plans.*, subjects.name AS subject_name
            FROM revision_plans
            JOIN subjects ON subjects.id = revision_plans.subject_id
            ORDER BY revision_plans.created_at DESC
            """
        ).fetchall()


def get_dashboard_counts():
    """Return simple counts for the dashboard cards."""
    with closing(get_connection()) as conn:
        subjects = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        documents = conn.execute(
            "SELECT COUNT(*) FROM uploaded_documents"
        ).fetchone()[0]
        flashcards = conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0]
        quizzes = conn.execute("SELECT COUNT(*) FROM quiz_results").fetchone()[0]
        return {
            "subjects": subjects,
            "documents": documents,
            "flashcards": flashcards,
            "quizzes": quizzes,
        }
