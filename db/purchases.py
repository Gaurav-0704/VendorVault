# Gaurav Singh Thakur — MIT License

from datetime import datetime
from db.connection import _connect, _local_now


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


def add_purchase_item(category_id, name, quantity, unit, price, notes=None, purchase_date=None):
    """Logs a purchase and updates the stock level for that category at the same time."""
    with _connect() as conn:
        ts = f'{purchase_date} 12:00:00' if purchase_date else _local_now()
        date_str = purchase_date or datetime.now().strftime('%Y-%m-%d')
        c = conn.execute(
            'INSERT INTO purchase_items (category_id, name, quantity, unit, price, notes, purchase_date, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (category_id, name, float(quantity), unit, float(price), notes, date_str, ts),
        )
        conn.execute(
            'INSERT OR REPLACE INTO stock_levels (category_id, quantity, unit, item_name, last_updated) '
            'VALUES (?, ?, ?, ?, ?)',
            (category_id, float(quantity), unit, name, date_str),
        )
        return c.lastrowid


def add_purchase_items_bulk(items, purchase_date=None):
    """Same as add_purchase_item but for a whole shopping run at once."""
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
                 item.get('notes', ''), date_str, ts),
            )
            ids.append(c.lastrowid)
            conn.execute(
                'INSERT OR REPLACE INTO stock_levels (category_id, quantity, unit, item_name, last_updated) '
                'VALUES (?, ?, ?, ?, ?)',
                (item['category_id'], float(item['quantity']),
                 item.get('unit', 'pcs'), item['name'], date_str),
            )
        return ids


def get_purchase_items(category_id=None):
    with _connect() as conn:
        if category_id:
            rows = conn.execute(
                'SELECT id, category_id, name, quantity, unit, price, notes, purchase_date, created_at '
                'FROM purchase_items WHERE category_id = ? ORDER BY created_at DESC',
                (category_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT id, category_id, name, quantity, unit, price, notes, purchase_date, created_at '
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


def update_stock(category_id, quantity, unit, item_name):
    with _connect() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO stock_levels (category_id, quantity, unit, item_name, last_updated) '
            'VALUES (?, ?, ?, ?, ?)',
            (category_id, float(quantity), unit, item_name, datetime.now().strftime('%Y-%m-%d')),
        )


def get_stock_levels():
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT sl.category_id, sl.quantity, sl.unit, sl.item_name, sl.last_updated, '
            'pc.name as category_name, pc.emoji '
            'FROM stock_levels sl '
            'JOIN purchase_categories pc ON sl.category_id = pc.id '
            'ORDER BY pc.name'
        ).fetchall()]
