# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Dashboard Routes

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template
from database import get_db

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/api/dashboard')
def dashboard():
    db    = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    week  = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
    month = datetime.now().strftime('%Y-%m-01')

    def stats(start, end=None):
        end = end or today
        row = db.execute('''
            SELECT COUNT(*)               AS total_orders,
                   COALESCE(SUM(subtotal), 0) AS revenue,
                   COALESCE(SUM(total_cost),0) AS cost,
                   COALESCE(SUM(profit),   0) AS profit
            FROM orders
            WHERE date(created_at) >= ? AND date(created_at) <= ?
              AND status != 'cancelled'
        ''', (start, end)).fetchone()
        return dict(row)

    top_items = db.execute('''
        SELECT oi.item_name,
               SUM(oi.quantity)    AS qty,
               SUM(oi.total_price) AS revenue
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE date(o.created_at) = ? AND o.status != 'cancelled'
        GROUP BY oi.item_name
        ORDER BY qty DESC LIMIT 5
    ''', (today,)).fetchall()

    recent = db.execute('''
        SELECT id, order_number, customer_name, source,
               subtotal, profit, status, created_at
        FROM orders ORDER BY created_at DESC LIMIT 10
    ''').fetchall()

    hourly = db.execute('''
        SELECT strftime('%H', created_at) AS hour,
               COUNT(*)                   AS orders,
               COALESCE(SUM(subtotal), 0) AS revenue
        FROM orders
        WHERE date(created_at) = ? AND status != 'cancelled'
        GROUP BY hour ORDER BY hour
    ''', (today,)).fetchall()

    return jsonify({
        'today':         stats(today),
        'this_week':     stats(week),
        'this_month':    stats(month),
        'top_items':     [dict(r) for r in top_items],
        'recent_orders': [dict(r) for r in recent],
        'hourly_sales':  [dict(r) for r in hourly],
    })


@bp.route('/api/quick-stats')
def quick_stats():
    db    = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    total_purchase = db.execute(
        "SELECT COALESCE(SUM(price), 0) FROM purchase_items"
    ).fetchone()[0]

    menu_count = db.execute(
        "SELECT COUNT(*) FROM menu_items WHERE is_available = 1"
    ).fetchone()[0]

    avg_margin = db.execute(
        "SELECT COALESCE(AVG(profit_margin), 0) FROM menu_items WHERE is_available = 1"
    ).fetchone()[0]

    today_orders = db.execute(
        "SELECT COUNT(*) FROM orders "
        "WHERE date(created_at) = ? AND status != 'cancelled'",
        (today,)
    ).fetchone()[0]

    return jsonify({
        'total_purchase_cost': round(total_purchase, 2),
        'total_menu_items':    menu_count,
        'avg_profit_margin':   round(avg_margin, 1),
        'today_orders':        today_orders,
    })
