# Gaurav Singh Thakur — MIT License

from flask import Blueprint, request, jsonify
from database import get_db

menu_bp = Blueprint('menu', __name__)


@menu_bp.route('/api/menu', methods=['GET'])
def list_menu():
    """Returns the full menu grouped by category — this is what the order screen loads."""
    db = get_db()
    categories = db.execute("SELECT * FROM menu_categories ORDER BY name").fetchall()
    result = []
    for cat in categories:
        items = db.execute(
            "SELECT * FROM menu_items WHERE category_id = ? ORDER BY name", (cat['id'],)
        ).fetchall()
        result.append({
            'id': cat['id'], 'name': cat['name'],
            'items': [{'id': i['id'], 'name': i['name'], 'price': i['price'], 'cost': round(i['cost'], 2),
                        'profit_per_item': round(i['profit_per_item'], 2),
                        'profit_margin': round(i['profit_margin'], 1),
                        'available': i['available']} for i in items]
        })
    db.close()
    return jsonify(result)


@menu_bp.route('/api/menu/items', methods=['POST'])
def add_menu_item():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO menu_items (category_id, name, price, cost) VALUES (?, ?, ?, ?)",
        (data['category_id'], data['name'], data['price'], data.get('cost', 0))
    )
    db.commit()
    item_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({'id': item_id, 'success': True}), 201


@menu_bp.route('/api/menu/items/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE menu_items SET name = ?, price = ?, cost = ?, available = ? WHERE id = ?",
        (data['name'], data['price'], data.get('cost', 0), data.get('available', 1), item_id)
    )
    db.commit()
    db.close()
    return jsonify({'success': True})


@menu_bp.route('/api/menu/items/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    db = get_db()
    db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})


@menu_bp.route('/api/menu/categories', methods=['POST'])
def add_menu_category():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO menu_categories (name) VALUES (?)", (data['name'],))
    db.commit()
    cat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({'id': cat_id, 'success': True}), 201


@menu_bp.route('/api/menu/categories/<int:cat_id>', methods=['DELETE'])
def delete_menu_category(cat_id):
    db = get_db()
    db.execute("DELETE FROM menu_items WHERE category_id = ?", (cat_id,))
    db.execute("DELETE FROM menu_categories WHERE id = ?", (cat_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})


@menu_bp.route('/api/menu/cost-breakdown')
def cost_breakdown():
    """I calculate per-unit ingredient costs from my purchase records and map them
    to each menu item so I know what each dish actually costs me to make."""
    db = get_db()
    purchases = db.execute("SELECT name, price, quantity, unit FROM purchase_items").fetchall()
    menu_items = db.execute("SELECT id, name, cost FROM menu_items").fetchall()

    ingredients = {}
    for item in purchases:
        name = item['name'].lower()
        qty = item['quantity'] if item['quantity'] > 0 else 1

        if name == 'eggs' or (item['unit'] == 'dozen' and 'egg' in name):
            total = qty * 12
            egg_each = item['price'] / total if total else 0
            ingredients['egg'] = {'price_each': round(egg_each, 4), 'unit': 'egg'}
        elif 'noodle' in name:
            each = item['price'] / qty
            ingredients['noodle'] = {'price_each': round(each, 3), 'unit': 'pack'}
        elif 'rice' in name:
            per_lb = item['price'] / qty
            ingredients['rice'] = {'price_each': round(per_lb, 4), 'unit': 'lb'}
        elif 'chicken' in name:
            per_lb = item['price'] / qty
            ingredients['chicken'] = {'price_each': round(per_lb, 3), 'unit': 'lb'}
        elif 'oil' in name:
            per_cup = item['price'] / qty
            ingredients['oil'] = {'price_each': round(per_cup, 3), 'unit': 'cup'}
        elif 'container' in name or 'packaging' in name.lower():
            each = item['price'] / qty
            ingredients['packaging'] = {'price_each': round(each, 3), 'unit': 'piece'}
        elif 'veg' in name or 'sauce' in name:
            ingredients['veggies'] = {'price_each': round(item['price'] / max(qty, 1), 2), 'unit': 'batch'}

    db.close()
    return jsonify({'ingredients': ingredients, 'menu_items': [
        {'id': m['id'], 'name': m['name'], 'cost': round(m['cost'], 3)} for m in menu_items
    ]})
