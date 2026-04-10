# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Report Routes

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from database import get_db

bp = Blueprint('reports', __name__)


@bp.route('/api/reports/daily')
def daily_report():
    db    = get_db()
    days  = request.args.get('days', 30, type=int)
    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    rows = db.execute('''
        SELECT date(created_at) AS date,
               COUNT(*)                    AS total_orders,
               COALESCE(SUM(subtotal), 0)  AS revenue,
               COALESCE(SUM(total_cost),0) AS cost,
               COALESCE(SUM(profit),   0)  AS profit
        FROM orders
        WHERE date(created_at) >= ? AND status != 'cancelled'
        GROUP BY date(created_at)
        ORDER BY date(created_at)
    ''', (start,)).fetchall()

    return jsonify([dict(r) for r in rows])


@bp.route('/api/reports/weekly')
def weekly_report():
    db    = get_db()
    weeks = request.args.get('weeks', 12, type=int)
    start = (datetime.now() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    rows = db.execute('''
        SELECT strftime('%%Y-W%%W', created_at) AS week,
               COUNT(*)                    AS total_orders,
               COALESCE(SUM(subtotal), 0)  AS revenue,
               COALESCE(SUM(total_cost),0) AS cost,
               COALESCE(SUM(profit),   0)  AS profit
        FROM orders
        WHERE date(created_at) >= ? AND status != 'cancelled'
        GROUP BY week ORDER BY week
    ''', (start,)).fetchall()

    return jsonify([dict(r) for r in rows])


@bp.route('/api/reports/monthly')
def monthly_report():
    db = get_db()
    rows = db.execute('''
        SELECT strftime('%%Y-%%m', created_at) AS month,
               COUNT(*)                    AS total_orders,
               COALESCE(SUM(subtotal), 0)  AS revenue,
               COALESCE(SUM(total_cost),0) AS cost,
               COALESCE(SUM(profit),   0)  AS profit
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY month ORDER BY month
    ''').fetchall()

    return jsonify([dict(r) for r in rows])


@bp.route('/api/reports/items')
def item_report():
    db        = get_db()
    date_from = request.args.get(
        'from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to   = request.args.get(
        'to', datetime.now().strftime('%Y-%m-%d'))

    rows = db.execute('''
        SELECT oi.item_name,
               SUM(oi.quantity)    AS total_qty,
               SUM(oi.total_price) AS total_revenue,
               SUM(oi.total_cost)  AS total_cost,
               SUM(oi.profit)      AS total_profit,
               ROUND(AVG(oi.profit / oi.quantity), 2) AS avg_profit_per_item
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE date(o.created_at) >= ? AND date(o.created_at) <= ?
          AND o.status != 'cancelled'
        GROUP BY oi.item_name
        ORDER BY total_qty DESC
    ''', (date_from, date_to)).fetchall()

    return jsonify([dict(r) for r in rows])


@bp.route('/api/reports/profit-breakdown')
def profit_breakdown():
    db = get_db()
    items = db.execute('''
        SELECT name, selling_price, cost_per_item,
               profit_per_item, profit_margin
        FROM menu_items WHERE is_available = 1
        ORDER BY profit_margin DESC
    ''').fetchall()
    return jsonify([dict(i) for i in items])
