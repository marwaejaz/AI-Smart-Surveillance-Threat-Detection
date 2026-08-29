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
def get_summary_counts():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM activity_log")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT alert_type, COUNT(*) FROM activity_log GROUP BY alert_type")
    by_type = dict(cursor.fetchall())
    conn.close()
    return total, by_type


def get_daily_counts(days=7):
    import datetime
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT substr(timestamp, 1, 10) AS day, COUNT(*) FROM activity_log GROUP BY day")
    counts = dict(cursor.fetchall())
    conn.close()
    today = datetime.date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        key = d.isoformat()
        result.append((key, counts.get(key, 0)))
    return result
 