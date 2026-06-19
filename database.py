# VendorVault - Restaurant Management System
# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.

import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager


def _local_now():
    """Get the current local timestamp as a formatted string."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendorvault.db')


# ============================================================================
# Database Connection and Context Management
# ============================================================================

@contextmanager
def _connect():
    """Establish a database connection with WAL mode and foreign keys enabled."""
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


# ============================================================================
# Database Initialization and Schema
# ============================================================================

def init_db():
    """Initialize the database with all required tables and default settings."""
    with _connect() as conn:
        c = conn.cursor()

        # Settings table: key-value pairs for application configuration
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Menu categories: groupings for menu items
        c.execute('''
            CREATE TABLE IF NOT EXISTS menu_categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Menu items: products sold to customers
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

        # Orders: customer transactions
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

        # Order items: line items in an order
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

        # Purchase categories: groupings for inventory items
        c.execute('''
            CREATE TABLE IF NOT EXISTS purchase_categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                emoji      TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Purchase items: inventory purchases
        c.execute('''
            CREATE TABLE IF NOT EXISTS purchase_items (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id   INTEGER NOT NULL,
                name          TEXT NOT NULL,
                quantity      REAL NOT NULL,
                unit          TEXT,
                price         REAL NOT NULL,
                notes         TEXT,
                purchase_date TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES purchase_categories(id) ON DELETE CASCADE
            )
        ''')

        # Add purchase_date column if it doesn't exist (migration for old databases)
        cols = [row[1] for row in c.execute('PRAGMA table_info(purchase_items)').fetchall()]
        if 'purchase_date' not in cols:
            c.execute('ALTER TABLE purchase_items ADD COLUMN purchase_date TEXT')

        # Expenses: payouts and miscellaneous expenses
        c.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                description  TEXT NOT NULL,
                amount       REAL NOT NULL,
                expense_date TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Stock levels: current inventory by category
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock_levels (
                category_id  INTEGER PRIMARY KEY,
                quantity     REAL NOT NULL DEFAULT 0,
                unit         TEXT,
                item_name    TEXT,
                last_updated TEXT,
                FOREIGN KEY (category_id) REFERENCES purchase_categories(id) ON DELETE CASCADE
            )
        ''')

        # Weekly cycles: financial tracking for operational weeks
        c.execute('''
            CREATE TABLE IF NOT EXISTS weekly_cycles (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start    TEXT NOT NULL,
                week_end      TEXT NOT NULL,
                starting_cash REAL NOT NULL DEFAULT 400,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Insert default settings
        defaults = [
            ('business_name', 'My Restaurant'),
            ('phone', ''),
            ('email', ''),
            ('address', ''),
            ('currency', 'USD'),
            ('cash_in_hand', '867'),
            ('weekly_start_amount', '400'),
        ]
        for key, val in defaults:
            c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))


# ============================================================================
# Settings Management
# ============================================================================

def get_all_settings():
    """Retrieve all application settings as a dictionary."""
    with _connect() as conn:
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        return {r['key']: r['value'] for r in rows}


def set_setting(key, value):
    """Set or update a single setting value."""
    with _connect() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))


# ============================================================================
# Menu Categories
# ============================================================================

def add_menu_category(name):
    """Add a new menu category. Returns the category ID."""
    with _connect() as conn:
        c = conn.execute('INSERT INTO menu_categories (name) VALUES (?)', (name,))
        return c.lastrowid


def get_menu_categories():
    """Retrieve all menu categories, sorted by name."""
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT id, name, created_at FROM menu_categories ORDER BY name'
        ).fetchall()]


def delete_menu_category(category_id):
    """Delete a menu category and all associated menu items."""
    with _connect() as conn:
        conn.execute('DELETE FROM menu_categories WHERE id = ?', (category_id,))


# ============================================================================
# Menu Items
# ============================================================================

def add_menu_item(category_id, name, price, cost):
    """Add a new menu item. Returns the item ID."""
    with _connect() as conn:
        c = conn.execute(
            'INSERT INTO menu_items (category_id, name, price, cost) VALUES (?, ?, ?, ?)',
            (category_id, name, float(price), float(cost))
        )
        return c.lastrowid


def get_menu_items(category_id=None):
    """Retrieve menu items, optionally filtered by category. Returns list of items."""
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
    """Retrieve a single menu item by ID. Returns dict or None."""
    with _connect() as conn:
        row = conn.execute(
            'SELECT id, category_id, name, price, cost FROM menu_items WHERE id = ?', (item_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_menu_item(item_id):
    """Delete a menu item."""
    with _connect() as conn:
        conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))


def update_menu_item(item_id, name=None, price=None, cost=None):
    """Update a menu item's details. Returns True if successful, False if not found."""
    with _connect() as conn:
        current = conn.execute(
            'SELECT id, name, price, cost FROM menu_items WHERE id = ?', (item_id,)
        ).fetchone()
        if not current:
            return False
        current = dict(current)
        c = conn.execute(
            'UPDATE menu_items SET name = ?, price = ?, cost = ? WHERE id = ?',
            (name or current['name'], float(price) if price is not None else current['price'],
             float(cost) if cost is not None else current['cost'], item_id)
        )
        return c.rowcount > 0


def get_menu_with_categories():
    """Retrieve all categories with their menu items nested."""
    cats = get_menu_categories()
    for cat in cats:
        cat['items'] = get_menu_items(cat['id'])
    return cats


# ============================================================================
# Orders
# ============================================================================

def _next_order_number():
    """Generate the next sequential order number."""
    with _connect() as conn:
        row = conn.execute('SELECT MAX(id) as peak FROM orders').fetchone()
        num = (row['peak'] or 0) + 1
        return f'ORD-{str(num).zfill(3)}'


def create_order(source, customer_name, customer_phone, notes, items, order_date=None):
    """Create a new order with line items.

    Args:
        source: Source of order (e.g., 'dine-in', 'delivery')
        customer_name: Name of customer
        customer_phone: Phone number of customer
        notes: Order notes
        items: List of dicts with 'menu_item_id' and 'quantity' keys
        order_date: Optional date string (YYYY-MM-DD) to backdate the order

    Returns: The order ID
    """
    with _connect() as conn:
        c = conn.cursor()
        order_num = _next_order_number()

        ts = f'{order_date} 12:00:00' if order_date else _local_now()
        c.execute(
            'INSERT INTO orders (order_number, source, customer_name, customer_phone, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (order_num, source or 'dine-in', customer_name, customer_phone, notes, ts)
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
    """Retrieve all orders with their items and calculated totals."""
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
    """Delete an order and all its associated items."""
    with _connect() as conn:
        conn.execute('DELETE FROM order_items WHERE order_id = ?', (order_id,))
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))


# ============================================================================
# Purchase Categories
# ============================================================================

def add_purchase_category(name, emoji=None):
    """Add a new purchase category. Returns the category ID."""
    with _connect() as conn:
        c = conn.execute(
            'INSERT INTO purchase_categories (name, emoji) VALUES (?, ?)', (name, emoji or '📦')
        )
        return c.lastrowid


def get_purchase_categories():
    """Retrieve all purchase categories, sorted by name."""
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT id, name, emoji, created_at FROM purchase_categories ORDER BY name'
        ).fetchall()]


def delete_purchase_category(category_id):
    """Delete a purchase category and all associated purchase items."""
    with _connect() as conn:
        conn.execute('DELETE FROM purchase_categories WHERE id = ?', (category_id,))


# ============================================================================
# Purchase Items
# ============================================================================

def add_purchase_item(category_id, name, quantity, unit, price, notes=None, purchase_date=None):
    """Add a purchase item and update stock levels. Returns the item ID."""
    with _connect() as conn:
        ts = f'{purchase_date} 12:00:00' if purchase_date else _local_now()
        date_str = purchase_date or datetime.now().strftime('%Y-%m-%d')
        c = conn.execute(
            'INSERT INTO purchase_items (category_id, name, quantity, unit, price, notes, purchase_date, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (category_id, name, float(quantity), unit, float(price), notes, date_str, ts)
        )
        conn.execute(
            'INSERT OR REPLACE INTO stock_levels (category_id, quantity, unit, item_name, last_updated) '
            'VALUES (?, ?, ?, ?, ?)',
            (category_id, float(quantity), unit, name, date_str)
        )
        return c.lastrowid


def add_purchase_items_bulk(items, purchase_date=None):
    """Add multiple purchase items in bulk. Returns list of item IDs.

    Args:
        items: List of dicts with 'category_id', 'name', 'quantity', 'price', and optional 'unit', 'notes'
        purchase_date: Optional date string (YYYY-MM-DD)
    """
    with _connect() as conn:
        ts = f'{purchase_date} 12:00:00' if purchase_date else _local_now()
        date_str = purchase_date or datetime.now().strftime('%Y-%m-%d')
        ids = []
        for item in items:
            c = conn.execute(
                'INSERT INTO purchase_items (category_id, name, quantity, unit, price, notes, purchase_date, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (item['category_id'], item['name'], float(item['quantity']),
                 item.get('unit', 'pcs'), float(item['price']),
                 item.get('notes', ''), date_str, ts)
            )
            ids.append(c.lastrowid)
            conn.execute(
                'INSERT OR REPLACE INTO stock_levels (category_id, quantity, unit, item_name, last_updated) '
                'VALUES (?, ?, ?, ?, ?)',
                (item['category_id'], float(item['quantity']),
                 item.get('unit', 'pcs'), item['name'], date_str)
            )
        return ids


def get_purchase_items(category_id=None):
    """Retrieve purchase items, optionally filtered by category."""
    with _connect() as conn:
        if category_id:
            rows = conn.execute(
                'SELECT id, category_id, name, quantity, unit, price, notes, purchase_date, created_at '
                'FROM purchase_items WHERE category_id = ? ORDER BY created_at DESC',
                (category_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT id, category_id, name, quantity, unit, price, notes, purchase_date, created_at '
                'FROM purchase_items ORDER BY created_at DESC'
            ).fetchall()
        return [dict(r) for r in rows]


def delete_purchase_item(item_id):
    """Delete a purchase item."""
    with _connect() as conn:
        conn.execute('DELETE FROM purchase_items WHERE id = ?', (item_id,))


def get_purchases_with_categories():
    """Retrieve all categories with their purchase items nested."""
    cats = get_purchase_categories()
    for cat in cats:
        cat['items'] = get_purchase_items(cat['id'])
    return cats


# ============================================================================
# Report Helpers
# ============================================================================

def _orders_in_range(conn, start_dt, end_dt):
    """Retrieve orders within a datetime range."""
    return [dict(r) for r in conn.execute(
        'SELECT id, source FROM orders WHERE created_at >= ? AND created_at <= ?',
        (start_dt, end_dt)
    ).fetchall()]


def _revenue_and_cost(conn, order_ids):
    """Calculate total revenue and cost for a list of order IDs."""
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


# ============================================================================
# Reports: Daily, Weekly, Monthly
# ============================================================================

def get_daily_report(date_str=None):
    """Get revenue, expenses, profit, and item breakdown for a specific day."""
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
    """Get revenue, expenses, profit, and daily breakdown for a week."""
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
    """Get revenue, expenses, profit, and weekly breakdown for a month."""
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


# ============================================================================
# Dashboard
# ============================================================================

def get_dashboard_stats():
    """Get aggregated stats: today, week, month, recent orders, hourly, top items."""
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


# ============================================================================
# Profits
# ============================================================================

def get_profits_data():
    """Get overall profit metrics and breakdown by product."""
    with _connect() as conn:
        row = conn.execute(
            'SELECT COALESCE(SUM(oi.price * oi.quantity), 0) as rev, '
            'COALESCE(SUM(oi.cost * oi.quantity), 0) as exp '
            'FROM order_items oi '
            'JOIN orders o ON oi.order_id = o.id'
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


# ============================================================================
# Cost Analysis
# ============================================================================

def get_cost_analysis():
    """Get cost breakdown by purchase category."""
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


# ============================================================================
# Expenses
# ============================================================================

def add_expense(description, amount, expense_date=None):
    """Add an expense. Returns the expense ID."""
    with _connect() as conn:
        ts = f'{expense_date} 12:00:00' if expense_date else _local_now()
        date_str = expense_date or datetime.now().strftime('%Y-%m-%d')
        c = conn.execute(
            'INSERT INTO expenses (description, amount, expense_date, created_at) '
            'VALUES (?, ?, ?, ?)',
            (description, float(amount), date_str, ts)
        )
        return c.lastrowid


def get_expenses():
    """Retrieve all expenses, sorted by creation date (newest first)."""
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT id, description, amount, expense_date, created_at '
            'FROM expenses ORDER BY created_at DESC'
        ).fetchall()]


def delete_expense(expense_id):
    """Delete an expense."""
    with _connect() as conn:
        conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))


# ============================================================================
# Stock Management
# ============================================================================

def update_stock(category_id, quantity, unit, item_name):
    """Update stock levels for a purchase category."""
    with _connect() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO stock_levels (category_id, quantity, unit, item_name, last_updated) '
            'VALUES (?, ?, ?, ?, ?)',
            (category_id, float(quantity), unit, item_name, datetime.now().strftime('%Y-%m-%d'))
        )


def get_stock_levels():
    """Retrieve all current stock levels with category information."""
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT sl.category_id, sl.quantity, sl.unit, sl.item_name, sl.last_updated, '
            'pc.name as category_name, pc.emoji '
            'FROM stock_levels sl '
            'JOIN purchase_categories pc ON sl.category_id = pc.id '
            'ORDER BY pc.name'
        ).fetchall()]


# ============================================================================
# Weekly Financial Cycle
# ============================================================================

def get_weekly_cycle_data():
    """Get the current week's financial cycle: Thu-Sun active, revenues and expenses tracked."""
    with _connect() as conn:
        cash_in_hand = compute_cash_in_hand()

        weekly_start = float(conn.execute(
            "SELECT value FROM settings WHERE key = 'weekly_start_amount'"
        ).fetchone()['value'] or 400)

        # Current week: Thursday through Sunday
        now = datetime.now()
        days_since_thu = (now.weekday() - 3) % 7
        this_thursday = (now - timedelta(days=days_since_thu)).strftime('%Y-%m-%d')
        this_sunday = (datetime.strptime(this_thursday, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')

        # Revenue earned this cycle (Thu-Sun)
        thu_start = datetime.strptime(this_thursday, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
        sun_end = datetime.strptime(this_sunday, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

        cycle_orders = _orders_in_range(conn, thu_start, sun_end)
        cycle_ids = [o['id'] for o in cycle_orders]
        cycle_revenue, cycle_cost = _revenue_and_cost(conn, cycle_ids)

        # Purchases this cycle
        purch_row = conn.execute(
            "SELECT COALESCE(SUM(price), 0) as total FROM purchase_items "
            "WHERE purchase_date >= ? AND purchase_date <= ?",
            (this_thursday, this_sunday)
        ).fetchone()
        cycle_purchases = purch_row['total']

        # Payouts this cycle
        exp_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
            "WHERE expense_date >= ? AND expense_date <= ?",
            (this_thursday, this_sunday)
        ).fetchone()
        cycle_payouts = exp_row['total']

        cycle_spent = cycle_purchases + cycle_payouts
        cycle_net = cycle_revenue - cycle_spent
        projected_end = weekly_start + cycle_net
        excess = max(0, projected_end - weekly_start)

        # Day-by-day breakdown
        daily = []
        cursor = datetime.strptime(this_thursday, '%Y-%m-%d')
        end_dt = datetime.strptime(this_sunday, '%Y-%m-%d')
        while cursor <= end_dt:
            ds = cursor.strftime('%Y-%m-%d')
            day_start = cursor.replace(hour=0, minute=0, second=0)
            day_end = cursor.replace(hour=23, minute=59, second=59)
            day_orders = _orders_in_range(conn, day_start, day_end)
            day_ids = [o['id'] for o in day_orders]
            day_rev, day_cst = _revenue_and_cost(conn, day_ids)

            day_purch = conn.execute(
                "SELECT COALESCE(SUM(price), 0) as t FROM purchase_items WHERE purchase_date = ?", (ds,)
            ).fetchone()['t']
            day_exp = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as t FROM expenses WHERE expense_date = ?", (ds,)
            ).fetchone()['t']

            daily.append({
                'date': ds,
                'dayName': cursor.strftime('%A'),
                'orders': len(day_orders),
                'revenue': round(day_rev, 2),
                'cost': round(day_cst, 2),
                'purchases': round(day_purch, 2),
                'payouts': round(day_exp, 2),
                'spent': round(day_purch + day_exp, 2),
                'profit': round(day_rev - day_cst - day_exp, 2),
                'net': round(day_rev - day_purch - day_exp, 2),
            })
            cursor += timedelta(days=1)

    return {
        'cashInHand': round(cash_in_hand, 2),
        'weeklyStartAmount': round(weekly_start, 2),
        'cycleStart': this_thursday,
        'cycleEnd': this_sunday,
        'cycleRevenue': round(cycle_revenue, 2),
        'cycleCost': round(cycle_cost, 2),
        'cyclePurchases': round(cycle_purchases, 2),
        'cyclePayouts': round(cycle_payouts, 2),
        'cycleSpent': round(cycle_spent, 2),
        'cycleNet': round(cycle_net, 2),
        'projectedEnd': round(projected_end, 2),
        'excess': round(excess, 2),
        'daily': daily,
    }


def get_end_of_day_report(date_str=None):
    """Get detailed end-of-day report: orders, items sold, revenues, costs, and profit."""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    start = dt.replace(hour=0, minute=0, second=0)
    end = dt.replace(hour=23, minute=59, second=59)

    with _connect() as conn:
        orders = _orders_in_range(conn, start, end)
        ids = [o['id'] for o in orders]
        revenue, cost = _revenue_and_cost(conn, ids)

        # Item breakdown
        items = []
        if ids:
            ph = ','.join('?' * len(ids))
            items = [dict(r) for r in conn.execute(
                f'SELECT mi.name, SUM(oi.quantity) as qty, '
                f'SUM(oi.price * oi.quantity) as revenue, '
                f'SUM(oi.cost * oi.quantity) as cost '
                f'FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id '
                f'WHERE oi.order_id IN ({ph}) GROUP BY mi.id ORDER BY qty DESC',
                ids
            ).fetchall()]

        # Purchases for the day
        day_purchases = conn.execute(
            "SELECT COALESCE(SUM(price), 0) as t FROM purchase_items WHERE purchase_date = ?",
            (date_str,)
        ).fetchone()['t']

        # Payouts for the day
        day_payouts = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as t FROM expenses WHERE expense_date = ?",
            (date_str,)
        ).fetchone()['t']

    profit = revenue - cost - day_payouts

    return {
        'date': date_str,
        'dayName': dt.strftime('%A'),
        'totalOrders': len(orders),
        'revenue': round(revenue, 2),
        'costOfGoods': round(cost, 2),
        'purchases': round(day_purchases, 2),
        'payouts': round(day_payouts, 2),
        'profit': round(profit, 2),
        'netCash': round(revenue - day_purchases - day_payouts, 2),
        'items': [{
            'name': i['name'],
            'qty': i['qty'],
            'revenue': round(i['revenue'], 2),
            'cost': round(i['cost'], 2),
            'profit': round(i['revenue'] - i['cost'], 2),
        } for i in items],
    }


# ============================================================================
# Finance Summary
# ============================================================================

def update_cash_in_hand(amount):
    """Update the weekly starting cash amount (default $400)."""
    set_setting('weekly_start_amount', str(round(float(amount), 2)))


def compute_cash_in_hand():
    """Compute live cash in hand for the current weekly cycle.

    Cash resets to the weekly start amount ($400) every Thursday.
    During the week: cash = $400 + revenue - purchases - payouts.
    """
    now = datetime.now()
    days_since_thu = (now.weekday() - 3) % 7
    this_thursday = (now - timedelta(days=days_since_thu)).strftime('%Y-%m-%d')
    this_sunday = (datetime.strptime(this_thursday, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')

    with _connect() as conn:
        weekly_start = float(conn.execute(
            "SELECT value FROM settings WHERE key = 'weekly_start_amount'"
        ).fetchone()['value'] or 400)

        # Revenue earned this cycle (Thu-Sun)
        thu_start = datetime.strptime(this_thursday, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
        sun_end = datetime.strptime(this_sunday, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

        cycle_orders = _orders_in_range(conn, thu_start, sun_end)
        cycle_ids = [o['id'] for o in cycle_orders]
        cycle_revenue, _ = _revenue_and_cost(conn, cycle_ids)

        # Purchases this cycle
        cycle_purchases = conn.execute(
            "SELECT COALESCE(SUM(price), 0) as total FROM purchase_items "
            "WHERE purchase_date >= ? AND purchase_date <= ?",
            (this_thursday, this_sunday)
        ).fetchone()['total']

        # Payouts this cycle
        cycle_payouts = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
            "WHERE expense_date >= ? AND expense_date <= ?",
            (this_thursday, this_sunday)
        ).fetchone()['total']

        return round(weekly_start + cycle_revenue - cycle_purchases - cycle_payouts, 2)


def get_finance_summary():
    """Get complete financial overview: revenues, purchases, expenses, profit, and recent transactions."""
    with _connect() as conn:
        # Total revenue and cost of goods from orders (joined to ensure no orphans)
        rev_cog = conn.execute(
            'SELECT COALESCE(SUM(oi.price * oi.quantity), 0) as revenue, '
            'COALESCE(SUM(oi.cost * oi.quantity), 0) as cog '
            'FROM order_items oi '
            'JOIN orders o ON oi.order_id = o.id'
        ).fetchone()
        total_revenue = rev_cog['revenue']
        total_cog = rev_cog['cog']

        # Total purchases
        purch_row = conn.execute(
            'SELECT COALESCE(SUM(price), 0) as total, COUNT(*) as cnt FROM purchase_items'
        ).fetchone()
        total_purchases = purch_row['total']

        # Total expenses (payouts)
        exp_row = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt FROM expenses'
        ).fetchone()
        total_expenses = exp_row['total']

        # Total orders
        ord_row = conn.execute('SELECT COUNT(*) as cnt FROM orders').fetchone()
        total_orders = ord_row['cnt']

        total_spent = total_purchases + total_expenses
        profit = total_revenue - total_cog - total_expenses
        cash_position = total_revenue - total_spent

        # Recent transactions (last 20 mixed)
        transactions = []

        # Order revenues by date
        order_txns = conn.execute(
            'SELECT o.created_at as date, SUM(oi.price * oi.quantity) as amount '
            'FROM orders o JOIN order_items oi ON o.id = oi.order_id '
            'GROUP BY o.id ORDER BY o.created_at DESC LIMIT 20'
        ).fetchall()
        for t in order_txns:
            transactions.append({
                'type': 'income', 'label': 'Order revenue',
                'amount': round(t['amount'], 2),
                'date': (t['date'] or '')[:10],
            })

        # Purchases
        purch_txns = conn.execute(
            'SELECT pi.name, pi.price, pi.purchase_date, pi.created_at, pc.emoji '
            'FROM purchase_items pi JOIN purchase_categories pc ON pi.category_id = pc.id '
            'ORDER BY pi.created_at DESC LIMIT 20'
        ).fetchall()
        for t in purch_txns:
            transactions.append({
                'type': 'purchase', 'label': f'{t["emoji"]} {t["name"]}',
                'amount': round(t['price'], 2),
                'date': t['purchase_date'] or (t['created_at'] or '')[:10],
            })

        # Expenses
        exp_txns = conn.execute(
            'SELECT description, amount, expense_date, created_at FROM expenses '
            'ORDER BY created_at DESC LIMIT 20'
        ).fetchall()
        for t in exp_txns:
            transactions.append({
                'type': 'payout', 'label': t['description'],
                'amount': round(t['amount'], 2),
                'date': t['expense_date'] or (t['created_at'] or '')[:10],
            })

        # Sort by date descending
        transactions.sort(key=lambda x: x['date'], reverse=True)

        # Weekly start amount
        ws_row = conn.execute(
            "SELECT value FROM settings WHERE key = 'weekly_start_amount'"
        ).fetchone()
        weekly_start = float(ws_row['value']) if ws_row else 400.0

    # Cash in hand = weekly cycle cash (resets to $400 each Thursday)
    live_cash = compute_cash_in_hand()

    return {
        'totalRevenue': round(total_revenue, 2),
        'totalPurchases': round(total_purchases, 2),
        'totalExpenses': round(total_expenses, 2),
        'totalSpent': round(total_spent, 2),
        'costOfGoods': round(total_cog, 2),
        'profit': round(profit, 2),
        'cashPosition': round(cash_position, 2),
        'cashInHand': round(live_cash, 2),
        'weeklyStartAmount': round(weekly_start, 2),
        'totalOrders': total_orders,
        'transactions': transactions[:30],
    }
