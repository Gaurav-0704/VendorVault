# Gaurav Singh Thakur — MIT License

from datetime import datetime
from db.connection import _connect, _local_now


def add_expense(description, amount, expense_date=None):
    with _connect() as conn:
        ts = f'{expense_date} 12:00:00' if expense_date else _local_now()
        date_str = expense_date or datetime.now().strftime('%Y-%m-%d')
        c = conn.execute(
            'INSERT INTO expenses (description, amount, expense_date, created_at) VALUES (?, ?, ?, ?)',
            (description, float(amount), date_str, ts),
        )
        return c.lastrowid


def get_expenses():
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT id, description, amount, expense_date, created_at FROM expenses ORDER BY created_at DESC'
        ).fetchall()]


def delete_expense(expense_id):
    with _connect() as conn:
        conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
