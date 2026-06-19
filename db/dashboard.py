# Gaurav Singh Thakur — MIT License

from datetime import datetime, timedelta
from db.connection import _connect
from db.reports import get_daily_report, get_weekly_report, get_monthly_report, _orders_in_range, _revenue_and_cost
from db.finance import compute_cash_in_hand


def get_dashboard_stats():
    """Everything the dashboard needs in one call — today, week, month, recent orders,
    hourly chart data, and top sellers. I keep it as one round-trip to keep the page fast."""
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
    week_end = now.strftime('%Y-%m-%d')
    month_str = now.strftime('%Y-%m')

    today_rpt = get_daily_report(today_str)
    week_rpt = get_weekly_report(week_start, week_end)
    month_rpt = get_monthly_report(month_str)

    with _connect() as conn:
        raw_orders = conn.execute(
            'SELECT id, order_number, source, customer_name, status, created_at '
            'FROM orders ORDER BY created_at DESC LIMIT 10'
        ).fetchall()
        recent = []
        for row in raw_orders:
            o = dict(row)
            sub = conn.execute(
                'SELECT COALESCE(SUM(price * quantity), 0) as total FROM order_items WHERE order_id = ?',
                (o['id'],),
            ).fetchone()
            recent.append({
                'id': o['id'],
                'orderNumber': o['order_number'],
                'customerName': o['customer_name'] or 'Walk-in',
                'source': o['source'],
                'status': o['status'],
                'amount': round(sub['total'], 2),
                'time': o['created_at'][11:16] if o['created_at'] and len(o['created_at']) > 15 else '',
            })

        today_orders = conn.execute(
            'SELECT id, created_at FROM orders WHERE created_at >= ? AND created_at <= ?',
            (today_start, today_end),
        ).fetchall()

        # Build hourly revenue buckets for the chart
        hour_map = {}
        for o in today_orders:
            try:
                h = int(o['created_at'][11:13])
            except (ValueError, IndexError, TypeError):
                h = 0
            if h not in hour_map:
                hour_map[h] = {'revenue': 0, 'orders': 0}
            hour_map[h]['orders'] += 1
            rev = conn.execute(
                'SELECT COALESCE(SUM(price * quantity), 0) as r FROM order_items WHERE order_id = ?',
                (o['id'],),
            ).fetchone()
            hour_map[h]['revenue'] += rev['r']

        # I show 8am–10pm even on slow days so the chart isn't empty
        hourly = []
        for h in range(24):
            if h in hour_map or (8 <= h <= 22):
                entry = hour_map.get(h, {'revenue': 0, 'orders': 0})
                hourly.append({
                    'time': f'{h:02d}:00',
                    'revenue': round(entry['revenue'], 2),
                    'orders': entry['orders'],
                })

        top_items = []
        today_ids = [o['id'] for o in today_orders]
        if today_ids:
            ph = ','.join('?' * len(today_ids))
            top_items = [dict(r) for r in conn.execute(
                f'SELECT mi.name, SUM(oi.quantity) as qty, SUM(oi.price * oi.quantity) as revenue '
                f'FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id '
                f'WHERE oi.order_id IN ({ph}) GROUP BY mi.id ORDER BY qty DESC LIMIT 10',
                today_ids,
            ).fetchall()]

        pending = conn.execute(
            "SELECT COUNT(*) as n FROM orders WHERE status = 'pending'"
        ).fetchone()['n']

    return {
        'today': {
            'revenue': today_rpt['revenue'],
            'expenses': today_rpt['expenses'],
            'profit': today_rpt['profit'],
            'orders': today_rpt['orders'],
            'pendingOrders': pending,
        },
        'week': {
            'revenue': week_rpt['revenue'],
            'expenses': week_rpt['expenses'],
            'profit': week_rpt['profit'],
            'orders': week_rpt['orders'],
        },
        'month': {
            'revenue': month_rpt['revenue'],
            'expenses': month_rpt['expenses'],
            'profit': month_rpt['profit'],
            'orders': month_rpt['orders'],
        },
        'recentOrders': recent,
        'hourly': hourly,
        'topItems': top_items,
    }
