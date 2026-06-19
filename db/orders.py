from datetime import datetime
from db.connection import _connect, _local_now
from db.menu import get_menu_item


def _next_order_number():
    with _connect() as conn:
        row = conn.execute('SELECT MAX(id) as peak FROM orders').fetchone()
        num = (row['peak'] or 0) + 1
        return f'ORD-{str(num).zfill(3)}'


def create_order(source, customer_name, customer_phone, notes, items, order_date=None):
    with _connect() as conn:
        c = conn.cursor()
        order_num = _next_order_number()
        ts = f'{order_date} 12:00:00' if order_date else _local_now()
        c.execute(
            'INSERT INTO orders (order_number, source, customer_name, customer_phone, notes, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (order_num, source or 'dine-in', customer_name, customer_phone, notes, ts),
        )
        order_id = c.lastrowid
        for item in items:
            mid = item.get('menu_item_id')
            qty = item.get('quantity', 1)
            menu_item = get_menu_item(mid)
            if menu_item:
                c.execute(
                    'INSERT INTO order_items (order_id, menu_item_id, quantity, price, cost) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (order_id, mid, qty, menu_item['price'], menu_item['cost']),
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
                (o['id'],),
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
