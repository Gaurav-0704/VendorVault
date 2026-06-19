# Gaurav Singh Thakur — MIT License

from flask import Blueprint, render_template, jsonify
from database import get_db
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    return render_template('index.html')


@dashboard_bp.route('/api/dashboard')
def dashboard_data():
    """Pulls today, this week, and this month stats in one shot for the dashboard page."""
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    month_start = datetime.now().strftime('%Y-%m-01')

    today_stats = db.execute("""
        SELECT COUNT(*) as orders, COALESCE(SUM(subtotal), 0) as revenue,
               COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE DATE(created_at) = ?
    """, (today,)).fetchone()

    week_stats = db.execute("""
        SELECT COUNT(*) as orders, COALESCE(SUM(subtotal), 0) as revenue,
               COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE DATE(created_at) >= ?
    """, (week_ago,)).fetchone()

    month_stats = db.execute("""
        SELECT COUNT(*) as orders, COALESCE(SUM(subtotal), 0) as revenue,
               COALESCE(SUM(profit), 0) as profit
        FROM orders WHERE DATE(created_at) >= ?
    """, (month_start,)).fetchone()

    top_items = db.execute("""
        SELECT item_name, SUM(quantity) as total_qty, SUM(line_total) as total_revenue
        FROM order_items oi JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.created_at) >= ?
        GROUP BY item_name ORDER BY total_qty DESC LIMIT 5
    """, (week_ago,)).fetchall()

    hourly = db.execute("""
        SELECT strftime('%H', created_at) as hour, COUNT(*) as orders,
               COALESCE(SUM(subtotal), 0) as revenue
        FROM orders WHERE DATE(created_at) = ?
        GROUP BY hour ORDER BY hour
    """, (today,)).fetchall()

    month_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses WHERE date >= ?
    """, (month_start,)).fetchone()

    db.close()

    return jsonify({
        'today': {'orders': today_stats['orders'], 'revenue': round(today_stats['revenue'], 2), 'profit': round(today_stats['profit'], 2)},
        'week': {'orders': week_stats['orders'], 'revenue': round(week_stats['revenue'], 2), 'profit': round(week_stats['profit'], 2)},
        'month': {'orders': month_stats['orders'], 'revenue': round(month_stats['revenue'], 2), 'profit': round(month_stats['profit'], 2)},
        'top_items': [{'name': r['item_name'], 'qty': r['total_qty'], 'revenue': round(r['total_revenue'], 2)} for r in top_items],
        'hourly': [{'hour': r['hour'], 'orders': r['orders'], 'revenue': round(r['revenue'], 2)} for r in hourly],
        'month_expenses': round(month_expenses['total'], 2),
    })


@dashboard_bp.route('/api/quick-stats')
def quick_stats():
    """Lighter version for the small widget tiles at the top of the dashboard."""
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    stats = db.execute("""
        SELECT COUNT(*) as orders, COALESCE(SUM(subtotal), 0) as revenue,
               COALESCE(SUM(profit), 0) as profit, COALESCE(SUM(total_cost), 0) as cost
        FROM orders WHERE DATE(created_at) = ?
    """, (today,)).fetchone()

    menu_count = db.execute("SELECT COUNT(*) as cnt FROM menu_items WHERE available = 1").fetchone()
    db.close()

    return jsonify({
        'today_orders': stats['orders'],
        'today_revenue': round(stats['revenue'], 2),
        'today_profit': round(stats['profit'], 2),
        'today_cost': round(stats['cost'], 2),
        'active_menu_items': menu_count['cnt'],
    })
