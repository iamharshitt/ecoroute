import sqlite3
import hashlib

def get_hash(prompt):
    return hashlib.md5(prompt.encode()).hexdigest()

def setup_cache():
    conn = sqlite3.connect('output/ecoroute_cache.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS responses (hash TEXT PRIMARY KEY, answer TEXT)''')
    conn.commit()
    return conn

def check_cache(conn, prompt):
    c = conn.cursor()
    c.execute('SELECT answer FROM responses WHERE hash=?', (get_hash(prompt),))
    result = c.fetchone()
    return result[0] if result else None

def save_cache(conn, prompt, answer):
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO responses (hash, answer) VALUES (?, ?)', (get_hash(prompt), answer))
    conn.commit()