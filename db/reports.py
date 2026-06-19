# Gaurav Singh Thakur — MIT License

from datetime import datetime, timedelta
from db.connection import _connect


# ---------------------------------------------------------------------------
# Shared query helpers — I use these in finance.py and dashboard.py too
# ---------------------------------------------------------------------------

def _orders_in_range(conn, start_dt, end_dt):
    """Grabs all order IDs and sources between two datetimes on an open connection."""
    return [dict(r) for r in conn.execute(
        'SELECT id, source FROM orders WHERE created_at >= ? AND created_at <= ?',
        (start_dt, end_dt),
    ).fetchall()]


def _revenue_and_cost(conn, order_ids):
    """Sums revenue and cost for a list of order IDs. Returns (0, 0) if the list is empty."""
    if not order_ids:
        return 0.0, 0.0
    ph = ','.join('?' * len(order_ids))
    row = conn.execute(
        f'SELECT COALESCE(SUM(price * quantity), 0) as rev, '
        f'COALESCE(SUM(cost * quantity), 0) as exp '
        f'FROM order_items WHERE order_id IN ({ph})',
        order_ids,
    ).fetchone()
    return row['rev'], row['exp']


# ---------------------------------------------------------------------------
# Daily / Weekly / Monthly reports
# ---------------------------------------------------------------------------

def get_daily_report(date_str=None):
    """Today's numbers by default, or whatever date I pass in."""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    start = dt.replace(hour=0, minute=0, second=0)
    end = dt.replace(hour=23, minute=59, second=59)
    with _connect() as conn:
        orders = _orders_in_range(conn, start, end)
        ids = [o['id'] for o in orders]
        revenue, cost = _revenue_and_cost(conn, ids)
        sources = {}
        for o in orders:
            s = o['source']
            sources[s] = sources.get(s, 0) + 1
        items = []
        if ids:
            ph = ','.join('?' * len(ids))
            items = [dict(r) for r in conn.execute(
                f'SELECT mi.name, SUM(oi.quantity) as qty, SUM(oi.price * oi.quantity) as revenue '
                f'FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id '
                f'WHERE oi.order_id IN ({ph}) GROUP BY mi.id ORDER BY qty DESC',
                ids,
            ).fetchall()]
    return {
        'revenue': round(revenue, 2),
        'expenses': round(cost, 2),
        'profit': round(revenue - cost, 2),
        'orders': len(orders),
        'sources': sources,
        'items': items,
    }


def get_weekly_report(start_str=None, end_str=None):
    """Defaults to the current Mon–Sun week if I don't pass dates."""
    if not start_str or not end_str:
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        start_str = monday.strftime('%Y-%m-%d')
        end_str = sunday.strftime('%Y-%m-%d')
    start = datetime.strptime(start_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
    end = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    with _connect() as conn:
        all_ids = [o['id'] for o in _orders_in_range(conn, start, end)]
        total_rev, total_cost = _revenue_and_cost(conn, all_ids)
        daily = []
        cursor = start
        while cursor <= end:
            day_start = cursor.replace(hour=0, minute=0, second=0)
            day_end = cursor.replace(hour=23, minute=59, second=59)
            day_ids = [o['id'] for o in _orders_in_range(conn, day_start, day_end)]
            day_rev, day_cost = _revenue_and_cost(conn, day_ids)
            daily.append({
                'date': cursor.strftime('%Y-%m-%d'),
                'revenue': round(day_rev, 2),
                'expenses': round(day_cost, 2),
                'orders': len(day_ids),
                'profit': round(day_rev - day_cost, 2),
            })
            cursor += timedelta(days=1)
    return {
        'revenue': round(total_rev, 2),
        'expenses': round(total_cost, 2),
        'profit': round(total_rev - total_cost, 2),
        'orders': len(all_ids),
        'daily': daily,
    }


def get_monthly_report(month_str=None):
    """Current month by default. Breaks it down week by week."""
    if not month_str:
        month_str = datetime.now().strftime('%Y-%m')
    year, month = [int(x) for x in month_str.split('-')]
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    with _connect() as conn:
        all_ids = [o['id'] for o in _orders_in_range(conn, start, end)]
        total_rev, total_cost = _revenue_and_cost(conn, all_ids)
        weekly = []
        cursor = start
        week_num = 1
        while cursor <= end:
            week_end = min(cursor + timedelta(days=6), end)
            w_ids = [o['id'] for o in _orders_in_range(conn, cursor, week_end.replace(hour=23, minute=59, second=59))]
            w_rev, w_cost = _revenue_and_cost(conn, w_ids)
            weekly.append({
                'week': f'Week {week_num}',
                'revenue': round(w_rev, 2),
                'expenses': round(w_cost, 2),
                'orders': len(w_ids),
                'profit': round(w_rev - w_cost, 2),
            })
            cursor += timedelta(days=7)
            week_num += 1
    return {
        'revenue': round(total_rev, 2),
        'expenses': round(total_cost, 2),
        'profit': round(total_rev - total_cost, 2),
        'orders': len(all_ids),
        'weekly': weekly,
    }


def get_profits_data():
    """Overall profit margin and a breakdown by menu item, sorted by most profitable."""
    with _connect() as conn:
        row = conn.execute(
            'SELECT COALESCE(SUM(oi.price * oi.quantity), 0) as rev, '
            'COALESCE(SUM(oi.cost * oi.quantity), 0) as exp '
            'FROM order_items oi JOIN orders o ON oi.order_id = o.id'
        ).fetchone()
        total_rev = row['rev']
        total_cost = row['exp']
        total_profit = total_rev - total_cost
        margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
        items = [dict(r) for r in conn.execute(
            'SELECT mi.name, '
            'SUM(oi.price * oi.quantity) as revenue, '
            'SUM(oi.cost * oi.quantity) as cost, '
            'SUM((oi.price - oi.cost) * oi.quantity) as profit '
            'FROM order_items oi '
            'JOIN orders o ON oi.order_id = o.id '
            'JOIN menu_items mi ON oi.menu_item_id = mi.id '
            'GROUP BY mi.id ORDER BY profit DESC'
        ).fetchall()]
        by_product = []
        for item in items:
            item_margin = (item['profit'] / item['revenue'] * 100) if item['revenue'] > 0 else 0
            by_product.append({
                'name': item['name'],
                'revenue': round(item['revenue'], 2),
                'cost': round(item['cost'], 2),
                'profit': round(item['profit'], 2),
                'margin': round(item_margin, 1),
            })
    return {
        'totalProfit': round(total_profit, 2),
        'totalRevenue': round(total_rev, 2),
        'totalCost': round(total_cost, 2),
        'profitMargin': round(margin, 1),
        'byProduct': by_product,
    }


def get_cost_analysis():
    """How much I've spent on purchases, grouped by category."""
    with _connect() as conn:
        total_row = conn.execute(
            'SELECT COALESCE(SUM(price), 0) as total, COUNT(*) as cnt FROM purchase_items'
        ).fetchone()
        total_cost = total_row['total']
        item_count = total_row['cnt']
        avg_cost = (total_cost / item_count) if item_count > 0 else 0
        cats = [dict(r) for r in conn.execute(
            'SELECT pc.id, pc.name, pc.emoji, '
            'COUNT(pi.id) as item_count, '
            'COALESCE(SUM(pi.price), 0) as total_cost, '
            'CASE WHEN COUNT(pi.id) > 0 THEN SUM(pi.price) / COUNT(pi.id) ELSE 0 END as avg_unit '
            'FROM purchase_categories pc '
            'LEFT JOIN purchase_items pi ON pc.id = pi.category_id '
            'GROUP BY pc.id ORDER BY total_cost DESC'
        ).fetchall()]
        by_category = [{
            'name': c['name'],
            'emoji': c['emoji'] or '📦',
            'itemCount': c['item_count'],
            'totalCost': round(c['total_cost'], 2),
            'avgUnitCost': round(c['avg_unit'], 2),
        } for c in cats]
    return {
        'totalCost': round(total_cost, 2),
        'avgCostPerItem': round(avg_cost, 2),
        'itemCount': item_count,
        'byCategory': by_category,
    }
