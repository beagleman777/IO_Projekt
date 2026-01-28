import sqlite3
from datetime import datetime, timedelta

DB_NAME = 'access_system.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, face_encoding BLOB, qr_code_id TEXT UNIQUE, is_active INTEGER DEFAULT 1)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, timestamp TEXT, status TEXT, failure_image BLOB)''')
    conn.commit()
    conn.close()


def add_user(name, user_id, face_encoding_bytes):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, face_encoding, qr_code_id, is_active) VALUES (?, ?, ?, 1)",
                  (name, face_encoding_bytes, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_user_status(qr_code_id, is_active):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_active = ? WHERE qr_code_id = ?", (1 if is_active else 0, qr_code_id))
    conn.commit()
    conn.close()


def get_user_by_qr(qr_code_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT face_encoding, name, is_active FROM users WHERE qr_code_id = ?", (qr_code_id,))
    result = c.fetchone()
    conn.close()
    return result


def log_access_attempt(user_id, status, image_bytes=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    img_to_save = image_bytes if status != "SUCCESS" else None
    c.execute("INSERT INTO logs (user_id, timestamp, status, failure_image) VALUES (?, ?, ?, ?)",
              (user_id, timestamp, status, img_to_save))
    conn.commit()
    conn.close()


def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, qr_code_id, is_active FROM users")
    data = c.fetchall()
    conn.close()
    return data


def cleanup_old_logs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("DELETE FROM logs WHERE timestamp < ?", (six_months_ago,))
    conn.commit()
    conn.close()
