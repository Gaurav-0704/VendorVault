# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Expense Routes

from datetime import datetime
from flask import Blueprint, request, jsonify
from database import get_db

bp = Blueprint('expenses', __name__)


@bp.route('/api/expenses')
def get_expenses():
    db    = get_db()
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    rows = db.execute(
        "SELECT * FROM expenses "
        "WHERE strftime('%%Y-%%m', date) = ? ORDER BY date DESC",
        (month,)
    ).fetchall()

    total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses "
        "WHERE strftime('%%Y-%%m', date) = ?",
        (month,)
    ).fetchone()[0]

    return jsonify({'expenses': [dict(r) for r in rows], 'total': total})


@bp.route('/api/expenses', methods=['POST'])
def add_expense():
    db   = get_db()
    data = request.json
    db.execute('''
        INSERT INTO expenses
            (category, description, amount, date, is_recurring, recurrence)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data.get('category', 'other'),
        data['description'],
        data['amount'],
        data.get('date', datetime.now().strftime('%Y-%m-%d')),
        data.get('is_recurring', 0),
        data.get('recurrence', ''),
    ))
    db.commit()
    return jsonify({'success': True})
