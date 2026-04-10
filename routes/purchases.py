# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Purchase Tracker Routes

from flask import Blueprint, request, jsonify
from database import get_db

bp = Blueprint('purchases', __name__)


@bp.route('/api/purchases')
def get_purchases():
    db = get_db()
    categories = db.execute(
        "SELECT * FROM purchase_categories ORDER BY name"
    ).fetchall()

    result = []
    for cat in categories:
        items = db.execute(
            "SELECT * FROM purchase_items WHERE category_id = ? ORDER BY name",
            (cat['id'],)
        ).fetchall()
        result.append({
            'category': dict(cat),
            'items':    [dict(i) for i in items],
        })
    return jsonify(result)


@bp.route('/api/purchases/item', methods=['POST'])
def add_purchase_item():
    db   = get_db()
    data = request.json
    db.execute('''
        INSERT INTO purchase_items
            (category_id, name, unit, quantity, price, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data['category_id'], data['name'],
        data.get('unit', 'unit'), data.get('quantity', 0),
        data.get('price', 0),    data.get('notes', ''),
    ))
    db.commit()
    return jsonify({'success': True, 'message': 'Purchase item added!'})


@bp.route('/api/purchases/item/<int:item_id>', methods=['PUT'])
def update_purchase_item(item_id):
    db   = get_db()
    data = request.json

    fields, values = [], []
    for key in ('name', 'unit', 'quantity', 'price', 'notes'):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(item_id)
        db.execute(
            f"UPDATE purchase_items SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        db.commit()
        _recalculate_menu_costs(db)

    return jsonify({'success': True})


@bp.route('/api/purchases/item/<int:item_id>', methods=['DELETE'])
def delete_purchase_item(item_id):
    db = get_db()
    db.execute("DELETE FROM purchase_items WHERE id = ?", (item_id,))
    db.commit()
    return jsonify({'success': True})


@bp.route('/api/purchases/category', methods=['POST'])
def add_purchase_category():
    db   = get_db()
    data = request.json
    db.execute(
        "INSERT INTO purchase_categories (name, icon) VALUES (?, ?)",
        (data['name'], data.get('icon', '📦')),
    )
    db.commit()
    return jsonify({'success': True})


# ── Helper: recalculate menu costs from current purchase prices ──────────

def _recalculate_menu_costs(db):
    items = db.execute(
        "SELECT name, price, quantity, unit FROM purchase_items"
    ).fetchall()

    chicken_per_g = egg_each = rice_per_cup = noodle_per_plate = 0

    for item in items:
        name = item['name'].lower()
        if 'chicken' in name:
            grams = item['quantity'] * 453.592
            chicken_per_g = item['price'] / grams if grams else 0
        elif name == 'eggs' or (item['unit'] == 'dozen' and 'egg' in name):
            total = item['quantity'] * 12
            egg_each = item['price'] / total if total else 0
        elif 'rice' in name and 'fried' not in name:
            cups = (item['quantity'] * 453.592) / 150
            rice_per_cup = item['price'] / cups if cups else 0
        elif 'noodle' in name:
            plates = item['quantity'] * 4
            noodle_per_plate = item['price'] / plates if plates else 0

    pkg = 0.22;  veg = 1.50;  oil = 0.30

    cost_map = {
        'Veg Noodles':           noodle_per_plate + veg + oil + pkg,
        'Egg Noodles':           noodle_per_plate + veg + oil + egg_each*2 + pkg,
        'Double Egg Noodles':    noodle_per_plate + veg + oil + egg_each*3 + pkg,
        'Chicken Noodles':       noodle_per_plate + veg + oil + chicken_per_g*70 + pkg,
        'Veg Fried Rice':        rice_per_cup + veg + oil + pkg,
        'Egg Fried Rice':        rice_per_cup + veg + oil + egg_each*2 + pkg,
        'Double Egg Fried Rice': rice_per_cup + veg + oil + egg_each*3 + pkg,
        'Chicken Fried Rice':    rice_per_cup + veg + oil + chicken_per_g*70 + pkg,
        'Chicken 65':            chicken_per_g*200 + veg + oil + pkg,
    }

    for item_name, cost in cost_map.items():
        db.execute(
            "UPDATE menu_items SET cost_per_item = ? WHERE name = ?",
            (round(cost, 2), item_name),
        )
    db.commit()
