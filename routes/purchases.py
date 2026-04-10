# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.

from flask import Blueprint, request, jsonify
from database import get_db

purchases_bp = Blueprint('purchases', __name__)


def _recalculate_menu_costs(db):
    """Recalculate all menu item costs based on current purchase prices."""
    items = db.execute("SELECT name, price, quantity, unit FROM purchase_items").fetchall()

    costs = {'pkg': 0.22, 'veg': 1.50, 'oil': 0.30,
             'egg': 0.153, 'chicken_per_lb': 4.0,
             'rice_per_lb': 0.363, 'noodle': 1.50}

    for item in items:
        name = item['name'].lower()
        qty = item['quantity'] if item['quantity'] > 0 else 1

        if name == 'eggs' or (item['unit'] == 'dozen' and 'egg' in name):
            total = qty * 12
            costs['egg'] = item['price'] / total if total else 0
        elif 'noodle' in name:
            costs['noodle'] = item['price'] / qty
        elif 'rice' in name:
            costs['rice_per_lb'] = item['price'] / qty
        elif 'chicken' in name:
            costs['chicken_per_lb'] = item['price'] / qty
        elif 'oil' in name:
            costs['oil'] = item['price'] / qty
        elif 'container' in name or 'packaging' in name:
            costs['pkg'] = item['price'] / qty
        elif 'veg' in name or 'sauce' in name:
            costs['veg'] = item['price'] / max(qty, 1)

    e2 = costs['egg'] * 2
    e3 = costs['egg'] * 3
    c70 = costs['chicken_per_lb'] * 0.0795  # 70g in lbs
    # 200g portion for appetizers
    c200 = costs['chicken_per_lb'] * 0.227

    # Per-serving rice: ~1lb per ~2.75 servings
    rice = costs['rice_per_lb'] * (1 / 2.75)

    menu_costs = {
        'Veg Noodles': costs['noodle'] + costs['veg'] + costs['oil'] + costs['pkg'],
        'Egg Noodles': costs['noodle'] + costs['veg'] + costs['oil'] + e2 + costs['pkg'],
        'Double Egg Noodles': costs['noodle'] + costs['veg'] + costs['oil'] + e3 + costs['pkg'],
        'Chicken Noodles': costs['noodle'] + costs['veg'] + costs['oil'] + c70 + costs['pkg'],
        'Veg Fried Rice': rice + costs['veg'] + costs['oil'] + costs['pkg'],
        'Egg Fried Rice': rice + costs['veg'] + costs['oil'] + e2 + costs['pkg'],
        'Double Egg Fried Rice': rice + costs['veg'] + costs['oil'] + e3 + costs['pkg'],
        'Chicken Fried Rice': rice + costs['veg'] + costs['oil'] + c70 + costs['pkg'],
        'Chicken 65': c200 + costs['veg'] + costs['oil'] + costs['pkg']
    }

    for name, cost in menu_costs.items():
        db.execute("UPDATE menu_items SET cost = ? WHERE name = ?", (round(cost, 3), name))


@purchases_bp.route('/api/purchases', methods=['GET'])
def list_purchases():
    """List all purchase categories and their items."""
    db = get_db()
    categories = db.execute("SELECT * FROM purchase_categories ORDER BY name").fetchall()
    result = []
    for cat in categories:
        items = db.execute(
            "SELECT * FROM purchase_items WHERE category_id = ? ORDER BY name", (cat['id'],)
        ).fetchall()
        result.append({
            'id': cat['id'], 'name': cat['name'], 'emoji': cat['emoji'],
            'items': [{'id': i['id'], 'name': i['name'], 'quantity': i['quantity'],
                        'unit': i['unit'], 'price': i['price'],
                        'price_per_unit': round(i['price_per_unit'], 4),
                        'notes': i['notes']} for i in items]
        })
    db.close()
    return jsonify(result)


@purchases_bp.route('/api/purchases/items', methods=['POST'])
def add_purchase_item():
    """Add a new purchase item and recalculate menu costs."""
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO purchase_items (category_id, name, quantity, unit, price, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (data['category_id'], data['name'], data.get('quantity', 1),
         data.get('unit', 'unit'), data['price'], data.get('notes', ''))
    )
    _recalculate_menu_costs(db)
    db.commit()
    item_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({'id': item_id, 'success': True}), 201


@purchases_bp.route('/api/purchases/items/<int:item_id>', methods=['PUT'])
def update_purchase_item(item_id):
    """Update a purchase item and recalculate menu costs."""
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE purchase_items SET name = ?, quantity = ?, unit = ?, price = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (data['name'], data.get('quantity', 1), data.get('unit', 'unit'),
         data['price'], data.get('notes', ''), item_id)
    )
    _recalculate_menu_costs(db)
    db.commit()
    db.close()
    return jsonify({'success': True})


@purchases_bp.route('/api/purchases/items/<int:item_id>', methods=['DELETE'])
def delete_purchase_item(item_id):
    """Remove a purchase item."""
    db = get_db()
    db.execute("DELETE FROM purchase_items WHERE id = ?", (item_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})


@purchases_bp.route('/api/purchases/categories', methods=['POST'])
def add_category():
    """Create a new purchase category."""
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO purchase_categories (name, emoji) VALUES (?, ?)",
        (data['name'], data.get('emoji', '📦'))
    )
    db.commit()
    cat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({'id': cat_id, 'success': True}), 201


@purchases_bp.route('/api/purchases/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    """Delete a purchase category and its items."""
    db = get_db()
    db.execute("DELETE FROM purchase_items WHERE category_id = ?", (cat_id,))
    db.execute("DELETE FROM purchase_categories WHERE id = ?", (cat_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})
