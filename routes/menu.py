# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Menu Routes

from flask import Blueprint, request, jsonify
from database import get_db

bp = Blueprint('menu', __name__)


@bp.route('/api/menu')
def get_menu():
    db = get_db()
    categories = db.execute(
        "SELECT * FROM menu_categories ORDER BY sort_order"
    ).fetchall()

    result = []
    for cat in categories:
        items = db.execute(
            "SELECT * FROM menu_items WHERE category_id = ? ORDER BY name",
            (cat['id'],)
        ).fetchall()
        result.append({
            'category': dict(cat),
            'items':    [dict(i) for i in items],
        })
    return jsonify(result)


@bp.route('/api/menu/item', methods=['POST'])
def add_menu_item():
    db   = get_db()
    data = request.json
    db.execute('''
        INSERT INTO menu_items
            (category_id, name, selling_price, cost_per_item, is_sunday_only, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data['category_id'], data['name'], data['selling_price'],
        data.get('cost_per_item', 0),
        data.get('is_sunday_only', 0),
        data.get('notes', ''),
    ))
    db.commit()
    return jsonify({'success': True, 'message': 'Menu item added!'})


@bp.route('/api/menu/item/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    db   = get_db()
    data = request.json
    db.execute('''
        UPDATE menu_items SET
            name           = COALESCE(?, name),
            selling_price  = COALESCE(?, selling_price),
            cost_per_item  = COALESCE(?, cost_per_item),
            is_available   = COALESCE(?, is_available),
            is_sunday_only = COALESCE(?, is_sunday_only),
            notes          = COALESCE(?, notes),
            updated_at     = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (
        data.get('name'), data.get('selling_price'),
        data.get('cost_per_item'), data.get('is_available'),
        data.get('is_sunday_only'), data.get('notes'),
        item_id,
    ))
    db.commit()
    return jsonify({'success': True})


@bp.route('/api/menu/item/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    db = get_db()
    db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    db.commit()
    return jsonify({'success': True})


@bp.route('/api/menu/cost-breakdown')
def cost_breakdown():
    db = get_db()
    items = db.execute(
        "SELECT name, price, quantity, unit FROM purchase_items"
    ).fetchall()

    chicken_per_g = egg_each = rice_per_cup = noodle_per_plate = 0
    oil_per_plate = 0.30
    veggies_per_plate = 1.50
    packaging = 0.22

    for item in items:
        n = item['name'].lower()
        u = item['unit'].lower() if item['unit'] else ''
        if 'chicken' in n:
            grams = item['quantity'] * 453.592
            chicken_per_g = item['price'] / grams if grams else 0
        elif n == 'eggs' or (u == 'dozen' and 'egg' in n):
            # Eggs bought in dozens: qty(dozens) × 12 = total eggs
            total = item['quantity'] * 12
            egg_each = item['price'] / total if total else 0
        elif 'rice' in n and 'fried' not in n:
            cups = (item['quantity'] * 453.592) / 150
            rice_per_cup = item['price'] / cups if cups else 0
        elif 'noodle' in n:
            plates = item['quantity'] * 4
            noodle_per_plate = item['price'] / plates if plates else 0
        elif 'oil' in n:
            oil_per_plate = (item['price'] * 0.5) / 15 if item['quantity'] else 0.30
        elif 'vegg' in n or 'sauce' in n:
            veggies_per_plate = item['price'] if item['price'] < 5 else 1.50
        elif 'container' in n:
            packaging = item['price'] / 150 if item['quantity'] else 0.11
        elif 'spoon' in n:
            packaging += item['price'] / 250 if item['quantity'] else 0
        elif 'bag' in n:
            packaging += item['price'] / 500 if item['quantity'] else 0

    breakdown = {
        'Veg Noodles':           [('Noodles (1/4 pkt)',noodle_per_plate),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Egg Noodles':           [('Noodles (1/4 pkt)',noodle_per_plate),('Eggs x2',egg_each*2),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Double Egg Noodles':    [('Noodles (1/4 pkt)',noodle_per_plate),('Eggs x3',egg_each*3),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Chicken Noodles':       [('Noodles (1/4 pkt)',noodle_per_plate),('Chicken 70g',chicken_per_g*70),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Veg Fried Rice':        [('Rice (1 cup)',rice_per_cup),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Egg Fried Rice':        [('Rice (1 cup)',rice_per_cup),('Eggs x2',egg_each*2),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Double Egg Fried Rice': [('Rice (1 cup)',rice_per_cup),('Eggs x3',egg_each*3),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Chicken Fried Rice':    [('Rice (1 cup)',rice_per_cup),('Chicken 70g',chicken_per_g*70),('Veggies & Sauces',veggies_per_plate),('Oil',oil_per_plate),('Packaging',packaging)],
        'Chicken 65':            [('Chicken 200g',chicken_per_g*200),('Spices & Batter',veggies_per_plate),('Oil (deep fry)',oil_per_plate),('Packaging',packaging)],
    }

    result = {}
    for item_name, ingredients in breakdown.items():
        result[item_name] = [
            {'ingredient': ing, 'cost': round(cost, 3)}
            for ing, cost in ingredients
        ]

    return jsonify(result)


@bp.route('/api/menu/category', methods=['POST'])
def add_menu_category():
    db   = get_db()
    data = request.json
    db.execute(
        "INSERT INTO menu_categories (name, icon, is_sunday_only) VALUES (?, ?, ?)",
        (data['name'], data.get('icon', '🍽️'), data.get('is_sunday_only', 0)),
    )
    db.commit()
    return jsonify({'success': True})
