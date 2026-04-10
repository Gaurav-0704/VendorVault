# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Order Routes

import json
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Response
from database import get_db

bp = Blueprint('orders', __name__)


@bp.route('/api/orders')
def get_orders():
    db          = get_db()
    date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    status      = request.args.get('status')
    source      = request.args.get('source')
    limit       = request.args.get('limit', 50, type=int)

    query  = "SELECT * FROM orders WHERE date(created_at) = ?"
    params = [date_filter]

    if status:
        query += " AND status = ?";  params.append(status)
    if source:
        query += " AND source = ?";  params.append(source)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    orders = db.execute(query, params).fetchall()
    result = []
    for order in orders:
        items = db.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order['id'],)
        ).fetchall()
        o = dict(order)
        o['items'] = [dict(i) for i in items]
        result.append(o)

    return jsonify(result)


@bp.route('/api/orders', methods=['POST'])
def create_order():
    db   = get_db()
    data = request.json

    today = datetime.now().strftime('%Y%m%d')
    count = db.execute(
        "SELECT COUNT(*) FROM orders WHERE order_number LIKE ?",
        (f'ORD-{today}%',)
    ).fetchone()[0]
    order_number = f"ORD-{today}-{count + 1:03d}"

    cursor = db.execute('''
        INSERT INTO orders
            (order_number, customer_name, customer_phone,
             source, status, subtotal, total_cost, profit, notes)
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?)
    ''', (
        order_number,
        data.get('customer_name', 'Walk-in'),
        data.get('customer_phone', ''),
        data.get('source', 'offline'),
        data.get('status', 'completed'),
        data.get('notes', ''),
    ))
    order_id = cursor.lastrowid

    subtotal   = 0
    total_cost = 0
    for item in data.get('items', []):
        menu_item = db.execute(
            "SELECT * FROM menu_items WHERE id = ?",
            (item['menu_item_id'],)
        ).fetchone()
        if not menu_item:
            continue

        qty         = item.get('quantity', 1)
        unit_price  = menu_item['selling_price']
        unit_cost   = menu_item['cost_per_item']
        item_total  = unit_price * qty
        item_cost   = unit_cost  * qty
        item_profit = item_total - item_cost

        db.execute('''
            INSERT INTO order_items
                (order_id, menu_item_id, item_name, quantity,
                 unit_price, unit_cost, total_price, total_cost, profit, extras)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id, menu_item['id'], menu_item['name'], qty,
            unit_price, unit_cost, item_total, item_cost, item_profit,
            json.dumps(item.get('extras', {})),
        ))
        subtotal   += item_total
        total_cost += item_cost

    profit = subtotal - total_cost
    db.execute(
        "UPDATE orders SET subtotal=?, total_cost=?, profit=? WHERE id=?",
        (round(subtotal, 2), round(total_cost, 2), round(profit, 2), order_id),
    )
    db.commit()

    return jsonify({
        'success':      True,
        'order_id':     order_id,
        'order_number': order_number,
        'subtotal':     round(subtotal, 2),
        'profit':       round(profit, 2),
    })


@bp.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    db   = get_db()
    data = request.json
    db.execute('''
        UPDATE orders
        SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (data.get('status', 'completed'), data.get('notes', ''), order_id))
    db.commit()
    return jsonify({'success': True})


@bp.route('/api/orders/<int:order_id>', methods=['DELETE'])
def cancel_order(order_id):
    db = get_db()
    db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
    db.commit()
    return jsonify({'success': True})


# ── CSV Export ───────────────────────────────────────────────────────────────

@bp.route('/api/export/orders')
def export_orders():
    db        = get_db()
    date_from = request.args.get(
        'from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to   = request.args.get(
        'to', datetime.now().strftime('%Y-%m-%d'))

    rows = db.execute('''
        SELECT o.order_number, o.customer_name, o.source, o.subtotal,
               o.total_cost, o.profit, o.status, o.created_at,
               GROUP_CONCAT(oi.item_name || ' x' || oi.quantity, ', ') AS items
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        WHERE date(o.created_at) >= ? AND date(o.created_at) <= ?
        GROUP BY o.id
        ORDER BY o.created_at DESC
    ''', (date_from, date_to)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Order #', 'Customer', 'Source', 'Items',
        'Revenue', 'Cost', 'Profit', 'Status', 'Date',
    ])
    for o in rows:
        writer.writerow([
            o['order_number'], o['customer_name'], o['source'],
            o['items'], o['subtotal'], o['total_cost'],
            o['profit'], o['status'], o['created_at'],
        ])

    filename = f'orders_{date_from}_to_{date_to}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
