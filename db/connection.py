# Gaurav Singh Thakur — MIT License
#
# Low-level connection setup. Everything else in db/ imports from here.

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

# In Railway/Docker I store the db in /app/data so a mounted volume persists it.
# Locally it sits next to app.py as before.
_DATA_DIR = os.environ.get('DB_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_DATA_DIR, 'vendorvault.db')


def _local_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_db():
    """Opens a bare connection — caller is responsible for commit and close.
    I use this in routes that need to hold a connection across several statements."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


@contextmanager
def _connect():
    """My go-to for everything in db/. Auto-commits on success, rolls back if something blows up."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
