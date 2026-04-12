# VendorVault - Restaurant Management System
# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
#
# One-time script to pre-load initial purchase data.
# Usage: python seed_purchases.py

from database import (
    init_db, get_purchase_categories, add_purchase_category,
    add_purchase_item
)

init_db()

# build category lookup
cats = {c['name']: c['id'] for c in get_purchase_categories()}

def ensure_cat(name, emoji):
    if name in cats:
        return cats[name]
    cid = add_purchase_category(name, emoji)
    cats[name] = cid
    print(f'Added category: {emoji} {name}')
    return cid

# user's actual purchase data — initial stock bought on 2026-04-07
purchase_date = '2026-04-07'

purchases = [
    ('Chicken',    '🍗', 'Chicken',          40,   'lbs',  82.40),
    ('Eggs',       '🥚', 'Eggs',             12,   'doz',  22.00),
    ('Rice',       '🍚', 'Rice',             20,   'lbs',  22.00),
    ('Noodles',    '🍜', 'Noodles',           1,   'pkt',   6.00),
    ('Oil',        '🫒', 'Cooking Oil',       1,   'gal',   9.00),
    ('Containers', '📦', 'Food Containers', 150,   'pcs',  16.50),
    ('Spoons',     '🥄', 'Plastic Spoons',  250,   'pcs',  12.50),
    ('Bags',       '🛍️', 'Plastic Bags',     500,   'pcs',  28.00),
]

for cat_name, emoji, item_name, qty, unit, price in purchases:
    cid = ensure_cat(cat_name, emoji)
    add_purchase_item(
        category_id=cid,
        name=item_name,
        quantity=qty,
        unit=unit,
        price=price,
        notes='Initial stock',
        purchase_date=purchase_date,
    )
    print(f'  {emoji} {item_name}: {qty} {unit} = ${price:.2f}')

total = sum(p[5] for p in purchases)
print(f'\nTotal purchases loaded: ${total:.2f}')
print('Done.')
