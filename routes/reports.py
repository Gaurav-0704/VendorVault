# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.

from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/api/reports/daily')
def daily_report():
    """Daily sales summary for a given date."""
    db = get_db()
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    summary = db.execute("""
        SELECT COUNT(*) as total_orders, COALESCE(SUM(subtotal), 0) as revenue,
               COALESCE(SUM(total_cost), 0) as cost, COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE DATE(created_at) = ?
    """, (date,)).fetchone()

    by_source = db.execute("""
        SELECT source, COUNT(*) as orders, COALESCE(SUM(subtotal), 0) as revenue
        FROM orders WHERE DATE(created_at) = ? GROUP BY source
    """, (date,)).fetchall()

    items = db.execute("""
        SELECT oi.item_name, SUM(oi.quantity) as qty, SUM(oi.line_total) as revenue,
               SUM(oi.line_cost) as cost
        FROM order_items oi JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.created_at) = ? GROUP BY oi.item_name ORDER BY qty DESC
    """, (date,)).fetchall()

    db.close()
    return jsonify({
        'date': date,
        'summary': {'orders': summary['total_orders'], 'revenue': round(summary['revenue'], 2),
                     'cost': round(summary['cost'], 2), 'profit': round(summary['profit'], 2)},
        'by_source': [{'source': r['source'], 'orders': r['orders'], 'revenue': round(r['revenue'], 2)} for r in by_source],
        'items': [{'name': r['item_name'], 'qty': r['qty'], 'revenue': round(r['revenue'], 2),
                    'cost': round(r['cost'], 2)} for r in items]
    })


@reports_bp.route('/api/reports/weekly')
def weekly_report():
    """Weekly sales summary."""
    db = get_db()
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    start = request.args.get('start', (datetime.strptime(end, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d'))

    daily = db.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as orders,
               COALESCE(SUM(subtotal), 0) as revenue, COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE DATE(created_at) BETWEEN ? AND ?
        GROUP BY DATE(created_at) ORDER BY date
    """, (start, end)).fetchall()

    totals = db.execute("""
        SELECT COUNT(*) as orders, COALESCE(SUM(subtotal), 0) as revenue,
               COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE DATE(created_at) BETWEEN ? AND ?
    """, (start, end)).fetchone()

    db.close()
    return jsonify({
        'start': start, 'end': end,
        'totals': {'orders': totals['orders'], 'revenue': round(totals['revenue'], 2), 'profit': round(totals['profit'], 2)},
        'daily': [{'date': r['date'], 'orders': r['orders'], 'revenue': round(r['revenue'], 2), 'profit': round(r['profit'], 2)} for r in daily]
    })


@reports_bp.route('/api/reports/monthly')
def monthly_report():
    """Monthly aggregated report."""
    db = get_db()
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    weekly = db.execute("""
        SELECT strftime('%W', created_at) as week, COUNT(*) as orders,
               COALESCE(SUM(subtotal), 0) as revenue, COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE strftime('%Y-%m', created_at) = ?
        GROUP BY week ORDER BY week
    """, (month,)).fetchall()

    totals = db.execute("""
        SELECT COUNT(*) as orders, COALESCE(SUM(subtotal), 0) as revenue,
               COALESCE(SUM(total_cost), 0) as cost, COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE strftime('%Y-%m', created_at) = ?
    """, (month,)).fetchone()

    expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE strftime('%Y-%m', date) = ?
    """, (month,)).fetchone()

    db.close()
    return jsonify({
        'month': month,
        'totals': {'orders': totals['orders'], 'revenue': round(totals['revenue'], 2),
                    'cost': round(totals['cost'], 2), 'profit': round(totals['profit'], 2),
                    'expenses': round(expenses['total'], 2),
                    'net_profit': round(totals['profit'] - expenses['total'], 2)},
        'weekly': [{'week': r['week'], 'orders': r['orders'], 'revenue': round(r['revenue'], 2),
                     'profit': round(r['profit'], 2)} for r in weekly]
    })


@reports_bp.route('/api/reports/items')
def item_performance():
    """Item-level sales performance ranking."""
    db = get_db()
    period = request.args.get('period', '30')
    cutoff = (datetime.now() - timedelta(days=int(period))).strftime('%Y-%m-%d')

    items = db.execute("""
        SELECT oi.item_name, SUM(oi.quantity) as total_qty,
               SUM(oi.line_total) as total_revenue, SUM(oi.line_cost) as total_cost,
               SUM(oi.line_total - oi.line_cost) as total_profit
        FROM order_items oi JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.created_at) >= ?
        GROUP BY oi.item_name ORDER BY total_qty DESC
    """, (cutoff,)).fetchall()

    db.close()
    return jsonify([{
        'name': r['item_name'], 'qty': r['total_qty'],
        'revenue': round(r['total_revenue'], 2), 'cost': round(r['total_cost'], 2),
        'profit': round(r['total_profit'], 2)
    } for r in items])
