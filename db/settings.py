# Gaurav Singh Thakur — MIT License

from db.connection import _connect


def get_all_settings():
    with _connect() as conn:
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        return {r['key']: r['value'] for r in rows}


def set_setting(key, value):
    with _connect() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
