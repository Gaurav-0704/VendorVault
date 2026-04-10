import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendorvault.db')


@contextmanager
def _connect():
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


# schema + defaults

def init_db():
    with _connect() as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS menu_categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS menu_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name        TEXT NOT NULL,
                price       REAL NOT NULL,
                cost        REAL NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES menu_categories(id) ON DELETE CASCADE
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number   TEXT UNIQUE NOT NULL,
                source         TEXT NOT NULL DEFAULT 'dine-in',
                customer_name  TEXT,
                customer_phone TEXT,
                notes          TEXT,
                status         TEXT DEFAULT 'completed',
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id     INTEGER NOT NULL,
                menu_item_id INTEGER NOT NULL,
                quantity     INTEGER NOT NULL,
                price        REAL NOT NULL,
                cost         REAL NOT NULL,
                FOREIGN KEY (order_id)     REFERENCES orders(id)     ON DELETE CASCADE,
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS purchase_categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                emoji      TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS purchase_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name        TEXT NOT NULL,
                quantity    REAL NOT NULL,
                unit        TEXT,
                price       REAL NOT NULL,
                notes       TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES purchase_categories(id) ON DELETE CASCADE
            )
        ''')

        # defaults (won't overwrite if user already changed them)
        defaults = [
            ('business_name', 'My Restaurant'),
            ('phone', ''),
            ('email', ''),
            ('address', ''),
            ('currency', 'USD'),
        ]
        for key, val in defaults:
            c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))


# settings

def get_all_settings():
    with _connect() as conn:
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        return {r['key']: r['value'] for r in rows}


def set_setting(key, value):
    with _connect() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))


# menu categories

def add_menu_category(name):
    with _connect() as conn:
        c = conn.execute('INSERT INTO menu_categories (name) VALUES (?)', (name,))
        return c.lastrowid


def get_menu_categories():
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT id, name, created_at FROM menu_categories ORDER BY name'
        ).fetchall()]


def delete_menu_category(category_id):
    with _connect() as conn:
        conn.execute('DELETE FROM menu_categories WHERE id = ?', (category_id,))


# menu items

def add_menu_item(category_id, name, price, cost):
    with _connect() as conn:
        c = conn.execute(
            'INSERT INTO menu_items (category_id, name, price, cost) VALUES (?, ?, ?, ?)',
            (category_id, name, float(price), float(cost))
        )
        return c.lastrowid


def get_menu_items(category_id=None):
    with _connect() as conn:
        if category_id:
            rows = conn.execute(
                'SELECT id, category_id, name, price, cost FROM menu_items WHERE category_id = ? ORDER BY name',
                (category_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT id, category_id, name, price, cost FROM menu_items ORDER BY name'
            ).fetchall()
        return [dict(r) for r in rows]


def get_menu_item(item_id):
    with _connect() as conn:
        row = conn.execute(
            'SELECT id, category_id, name, price, cost FROM menu_items WHERE id = ?', (item_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_menu_item(item_id):
    with _connect() as conn:
        conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))


def get_menu_with_categories():
    cats = get_menu_categories()
    for cat in cats:
        cat['items'] = get_menu_items(cat['id'])
    return cats


# orders

def _next_order_number():
    with _connect() as conn:
        row = conn.execute('SELECT MAX(id) as peak FROM orders').fetchone()
        num = (row['peak'] or 0) + 1
        return f'ORD-{str(num).zfill(3)}'


def create_order(source, customer_name, customer_phone, notes, items):
    # items: list of {menu_item_id, quantity} — prices come from the menu
    with _connect() as conn:
        c = conn.cursor()
        order_num = _next_order_number()

        c.execute(
            'INSERT INTO orders (order_number, source, customer_name, customer_phone, notes) VALUES (?, ?, ?, ?, ?)',
            (order_num, source or 'dine-in', customer_name, customer_phone, notes)
        )
        order_id = c.lastrowid

        for item in items:
            mid = item.get('menu_item_id')
            qty = item.get('quantity', 1)
            menu_item = get_menu_item(mid)
            if menu_item:
                c.execute(
                    'INSERT INTO order_items (order_id, menu_item_id, quantity, price, cost) VALUES (?, ?, ?, ?, ?)',
                    (order_id, mid, qty, menu_item['price'], menu_item['cost'])
                )

        return order_id


def get_orders():
    with _connect() as conn:
        c = conn.cursor()
        rows = c.execute(
            'SELECT id, order_number, source, customer_name, customer_phone, notes, status, created_at '
            'FROM orders ORDER BY created_at DESC'
        ).fetchall()

        orders = []
        for row in rows:
            o = dict(row)
            items = [dict(i) for i in c.execute(
                'SELECT id, menu_item_id, quantity, price, cost FROM order_items WHERE order_id = ?',
                (o['id'],)
            ).fetchall()]

            subtotal = sum(i['price'] * i['quantity'] for i in items)
            total_cost = sum(i['cost'] * i['quantity'] for i in items)

            o['items'] = items
            o['subtotal'] = round(subtotal, 2)
            o['total_cost'] = round(total_cost, 2)
            o['profit'] = round(subtotal - total_cost, 2)
            orders.append(o)

        return orders


def delete_order(order_id):
    with _connect() as conn:
        conn.execute('DELETE FROM order_items WHERE order_id = ?', (order_id,))
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))


# purchases

def add_purchase_category(name, emoji=None):
    with _connect() as conn:
        c = conn.execute(
            'INSERT INTO purchase_categories (name, emoji) VALUES (?, ?)', (name, emoji or '📦')
        )
        return c.lastrowid


def get_purchase_categories():
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT id, name, emoji, created_at FROM purchase_categories ORDER BY name'
        ).fetchall()]


def delete_purchase_category(category_id):
    with _connect() as conn:
        conn.execute('DELETE FROM purchase_categories WHERE id = ?', (category_id,))


def add_purchase_item(category_id, name, quantity, unit, price, notes=None):
    with _connect() as conn:
        c = conn.execute(
            'INSERT INTO purchase_items (category_id, name, quantity, unit, price, notes) VALUES (?, ?, ?, ?, ?, ?)',
            (category_id, name, float(quantity), unit, float(price), notes)
        )
        return c.lastrowid


def get_purchase_items(category_id=None):
    with _connect() as conn:
        if category_id:
            rows = conn.execute(
                'SELECT id, category_id, name, quantity, unit, price, notes, created_at '
                'FROM purchase_items WHERE category_id = ? ORDER BY created_at DESC',
                (category_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT id, category_id, name, quantity, unit, price, notes, created_at '
                'FROM purchase_items ORDER BY created_at DESC'
            ).fetchall()
        return [dict(r) for r in rows]


def delete_purchase_item(item_id):
    with _connect() as conn:
        conn.execute('DELETE FROM purchase_items WHERE id = ?', (item_id,))


def get_purchases_with_categories():
    cats = get_purchase_categories()
    for cat in cats:
        cat['items'] = get_purchase_items(cat['id'])
    return cats


# report helpers

def _orders_in_range(conn, start_dt, end_dt):
    return [dict(r) for r in conn.execute(
        'SELECT id, source FROM orders WHERE created_at >= ? AND created_at <= ?',
        (start_dt, end_dt)
    ).fetchall()]


def _revenue_and_cost(conn, order_ids):
    if not order_ids:
        return 0.0, 0.0
    ph = ','.join('?' * len(order_ids))
    row = conn.execute(
        f'SELECT COALESCE(SUM(price * quantity), 0) as rev, '
        f'COALESCE(SUM(cost * quantity), 0) as exp '
        f'FROM order_items WHERE order_id IN ({ph})',
        order_ids
    ).fetchone()
    return row['rev'], row['exp']


# reports

def get_daily_report(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    start = dt.replace(hour=0, minute=0, second=0)
    end = dt.replace(hour=23, minute=59, second=59)

    with _connect() as conn:
        orders = _orders_in_range(conn, start, end)
        ids = [o['id'] for o in orders]
        revenue, cost = _revenue_and_cost(conn, ids)

        # source breakdown
        sources = {}
        for o in orders:
            s = o['source']
            sources[s] = sources.get(s, 0) + 1

        # item breakdown
        items = []
        if ids:
            ph = ','.join('?' * len(ids))
            items = [dict(r) for r in conn.execute(
                f'SELECT mi.name, SUM(oi.quantity) as qty, SUM(oi.price * oi.quantity) as revenue '
                f'FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id '
                f'WHERE oi.order_id IN ({ph}) GROUP BY mi.id ORDER BY qty DESC',
                ids
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


# dashboard

def get_dashboard_stats():
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
        # Recent orders with totals
        raw_orders = conn.execute(
            'SELECT id, order_number, source, customer_name, status, created_at '
            'FROM orders ORDER BY created_at DESC LIMIT 10'
        ).fetchall()

        recent = []
        for row in raw_orders:
            o = dict(row)
            sub = conn.execute(
                'SELECT COALESCE(SUM(price * quantity), 0) as total FROM order_items WHERE order_id = ?',
                (o['id'],)
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

        # Hourly breakdown for today
        today_orders = conn.execute(
            'SELECT id, created_at FROM orders WHERE created_at >= ? AND created_at <= ?',
            (today_start, today_end)
        ).fetchall()

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
                (o['id'],)
            ).fetchone()
            hour_map[h]['revenue'] += rev['r']

        hourly = []
        for h in range(24):
            if h in hour_map or (8 <= h <= 22):
                entry = hour_map.get(h, {'revenue': 0, 'orders': 0})
                hourly.append({
                    'time': f'{h:02d}:00',
                    'revenue': round(entry['revenue'], 2),
                    'orders': entry['orders'],
                })

        # Top selling items today
        top_items = []
        today_ids = [o['id'] for o in today_orders]
        if today_ids:
            ph = ','.join('?' * len(today_ids))
            top_items = [dict(r) for r in conn.execute(
                f'SELECT mi.name, SUM(oi.quantity) as qty, SUM(oi.price * oi.quantity) as revenue '
                f'FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id '
                f'WHERE oi.order_id IN ({ph}) GROUP BY mi.id ORDER BY qty DESC LIMIT 10',
                today_ids
            ).fetchall()]

        # Pending order count
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


# profits

def get_profits_data():
    with _connect() as conn:
        row = conn.execute(
            'SELECT COALESCE(SUM(price * quantity), 0) as rev, '
            'COALESCE(SUM(cost * quantity), 0) as exp '
            'FROM order_items'
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


# cost analysis

def get_cost_analysis():
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
