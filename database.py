import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "security_system.db")

def init_db():
    """Initializes the SQLite database and creates the activity log table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            detail TEXT,
            snapshot TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_event(timestamp, alert_type, detail, snapshot=""):
    """Inserts a new security event into the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_log (timestamp, alert_type, detail, snapshot)
        VALUES (?, ?, ?, ?)
    """, (timestamp, alert_type, detail, snapshot))
    conn.commit()
    conn.close()

def get_logs(limit=100):
    """Fetches recent security logs from the database for the dashboard."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, alert_type, detail, snapshot 
        FROM activity_log 
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows