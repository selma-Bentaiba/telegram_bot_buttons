import sqlite3
from datetime import datetime, date

class Database:
    def __init__(self, db_path="tracker.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS friends (
                user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
                status TEXT DEFAULT 'member', joined_date TEXT,
                notes TEXT, last_seen TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS invite_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT, friend_name TEXT,
                link TEXT UNIQUE, created_date TEXT, used_by INTEGER)""")
            c.execute("""CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                username TEXT, name TEXT, message_id INTEGER,
                action_type TEXT, timestamp TEXT)""")
            conn.commit()
    
    def add_friend(self, user_id, name, username=None):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute("INSERT OR REPLACE INTO friends VALUES (?,?,?,'member',?,?,?)",
                     (user_id, name, username, now, None, now))
            conn.commit()
    
    def update_friend_status(self, user_id, status):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE friends SET status=?, last_seen=? WHERE user_id=?",
                     (status, datetime.now().isoformat(), user_id))
            conn.commit()
    
    def get_friend(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM friends WHERE user_id=?", (user_id,))
            return c.fetchone()
    
    def get_all_friends(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM friends ORDER BY joined_date DESC")
            return c.fetchall()
    
    def add_invite_link(self, name, link):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO invite_links (friend_name, link, created_date) VALUES (?,?,?)",
                     (name, link, datetime.now().isoformat()))
            conn.commit()
    
    def log_click(self, user_id, username, name, message_id, action_type):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO clicks (user_id, username, name, message_id, action_type, timestamp) VALUES (?,?,?,?,?,?)",
                     (user_id, username, name, message_id, action_type, datetime.now().isoformat()))
            conn.commit()
    
    def get_post_clicks(self, message_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM clicks WHERE message_id=? ORDER BY timestamp DESC", (message_id,))
            return c.fetchall()
    
    def get_user_clicks(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM clicks WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
            return c.fetchall()
    
    def get_today_joins(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            today = date.today().isoformat()
            c.execute("SELECT * FROM friends WHERE joined_date LIKE ?", (f"{today}%",))
            return c.fetchall()
    
    def get_today_clicks(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            today = date.today().isoformat()
            c.execute("SELECT * FROM clicks WHERE timestamp LIKE ?", (f"{today}%",))
            return c.fetchall()
    
    def add_note(self, user_id, note):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE friends SET notes=? WHERE user_id=?", (note, user_id))
            conn.commit()
