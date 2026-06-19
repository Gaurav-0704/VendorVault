# Gaurav Singh Thakur — MIT License

from flask import Blueprint, request, jsonify, Response
from database import get_db
from datetime import datetime
import csv
import io

orders_bp = Blueprint('orders', __name__)


def generate_order_number(db):
    """I format order numbers as ORD-YYYYMMDD-NNN so they're easy to read at a glance."""
    today = datetime.now().strftime('%Y%m%d')
    prefix = f'ORD-{today}-'
    last = db.execute(
        "SELECT order_number FROM orders WHERE order_number LIKE ? ORDER BY id DESC LIMIT 1",
        (prefix + '%',)
    ).fetchone()
    num = 1
    if last:
        try:
            num = int(last['order_number'].split('-')[-1]) + 1
        except ValueError:
            num = 1
    return f'{prefix}{num:03d}'


@orders_bp.route('/api/orders', methods=['GET'])
def list_orders():
    """I can filter by date range or source — handy for checking a specific day's orders."""
    db = get_db()
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    source = request.args.get('source', '')
    limit = request.args.get('limit', 50, type=int)

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if date_from:
        query += " AND DATE(created_at) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND DATE(created_at) <= ?"
        params.append(date_to)
    if source:
        query += " AND source = ?"
        params.append(source)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    orders = db.execute(query, params).fetchall()
    result = []
    for o in orders:
        items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (o['id'],)).fetchall()
        result.append({
            'id': o['id'], 'order_number': o['order_number'], 'source': o['source'],
            'customer_name': o['customer_name'], 'customer_phone': o['customer_phone'],
            'subtotal': o['subtotal'], 'total_cost': o['total_cost'], 'profit': o['profit'],
            'status': o['status'], 'notes': o['notes'], 'created_at': o['created_at'],
            'items': [{'id': i['id'], 'item_name': i['item_name'], 'quantity': i['quantity'],
                       'unit_price': i['unit_price'], 'unit_cost': i['unit_cost'],
                       'line_total': i['line_total']} for i in items]
        })

    db.close()
    return jsonify(result)


@orders_bp.route('/api/orders', methods=['POST'])
def create_order():
    """Places a new order and locks in the current menu prices at time of sale."""
    data = request.json
    db = get_db()
    order_num = generate_order_number(db)

    items = data.get('items', [])
    subtotal = 0
    total_cost = 0

    db.execute(
        """INSERT INTO orders (order_number, source, customer_name, customer_phone, subtotal, total_cost, notes)
           VALUES (?, ?, ?, ?, 0, 0, ?)""",
        (order_num, data.get('source', 'walk-in'), data.get('customer_name', ''),
         data.get('customer_phone', ''), data.get('notes', ''))
    )
    order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    for item in items:
        menu_item = db.execute("SELECT * FROM menu_items WHERE id = ?", (item['menu_item_id'],)).fetchone()
        if not menu_item:
            continue
        qty = item.get('quantity', 1)
        unit_price = menu_item['price']
        unit_cost = menu_item['cost']
        subtotal += qty * unit_price
        total_cost += qty * unit_cost

        db.execute(
            """INSERT INTO order_items (order_id, menu_item_id, item_name, quantity, unit_price, unit_cost)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, menu_item['id'], menu_item['name'], qty, unit_price, unit_cost)
        )

    db.execute("UPDATE orders SET subtotal = ?, total_cost = ? WHERE id = ?",
               (round(subtotal, 2), round(total_cost, 2), order_id))
    db.commit()
    db.close()

    return jsonify({'id': order_id, 'order_number': order_num, 'subtotal': round(subtotal, 2),
                    'total_cost': round(total_cost, 2), 'profit': round(subtotal - total_cost, 2)}), 201


@orders_bp.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    data = request.json
    db = get_db()
    db.execute("UPDATE orders SET status = ?, notes = ? WHERE id = ?",
               (data.get('status', 'completed'), data.get('notes', ''), order_id))
    db.commit()
    db.close()
    return jsonify({'success': True})


@orders_bp.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    db = get_db()
    db.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
    db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})


@orders_bp.route('/api/export/orders')
def export_orders():
    """Dumps everything to CSV — I use this when I need to review a period in a spreadsheet."""
    db = get_db()
    orders = db.execute("""
        SELECT o.order_number, o.source, o.customer_name, o.created_at,
               oi.item_name, oi.quantity, oi.unit_price, oi.line_total, oi.unit_cost,
               o.subtotal, o.total_cost, o.profit
        FROM orders o JOIN order_items oi ON o.id = oi.order_id
        ORDER BY o.created_at DESC
    """).fetchall()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order #', 'Source', 'Customer', 'Date', 'Item', 'Qty',
                     'Unit Price', 'Line Total', 'Unit Cost', 'Order Total', 'Order Cost', 'Profit'])
    for row in orders:
        writer.writerow([row['order_number'], row['source'], row['customer_name'],
                         row['created_at'], row['item_name'], row['quantity'],
                         row['unit_price'], row['line_total'], row['unit_cost'],
                         row['subtotal'], row['total_cost'], row['profit']])

    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=orders_export.csv'})
