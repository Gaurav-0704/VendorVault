# Gaurav Singh Thakur — MIT License

from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/api/expenses', methods=['GET'])
def list_expenses():
    """Defaults to the current month. I can pass ?month=YYYY-MM to look at older ones."""
    db = get_db()
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    expenses = db.execute(
        "SELECT * FROM expenses WHERE strftime('%Y-%m', date) = ? ORDER BY date DESC",
        (month,)
    ).fetchall()

    total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE strftime('%Y-%m', date) = ?",
        (month,)
    ).fetchone()

    by_category = db.execute("""
        SELECT category, COALESCE(SUM(amount), 0) as total, COUNT(*) as count
        FROM expenses WHERE strftime('%Y-%m', date) = ?
        GROUP BY category ORDER BY total DESC
    """, (month,)).fetchall()

    db.close()
    return jsonify({
        'expenses': [{'id': e['id'], 'category': e['category'], 'description': e['description'],
                       'amount': e['amount'], 'date': e['date'], 'notes': e['notes']} for e in expenses],
        'total': round(total['total'], 2),
        'by_category': [{'category': c['category'], 'total': round(c['total'], 2), 'count': c['count']} for c in by_category],
    })


@expenses_bp.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO expenses (category, description, amount, date, notes) VALUES (?, ?, ?, ?, ?)",
        (data.get('category', 'other'), data.get('description', ''),
         data['amount'], data.get('date', datetime.now().strftime('%Y-%m-%d')),
         data.get('notes', ''))
    )
    db.commit()
    expense_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({'id': expense_id, 'success': True}), 201


@expenses_bp.route('/api/expenses/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE expenses SET category = ?, description = ?, amount = ?, date = ?, notes = ? WHERE id = ?",
        (data.get('category', 'other'), data.get('description', ''),
         data['amount'], data.get('date'), data.get('notes', ''), expense_id)
    )
    db.commit()
    db.close()
    return jsonify({'success': True})


@expenses_bp.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})
