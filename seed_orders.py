# VendorVault - Restaurant Management System
# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
#
# One-time script to add historical orders.
# Usage: python seed_orders.py

from database import (
    init_db, create_order, get_menu_items,
    get_menu_categories, add_menu_category, add_menu_item
)

init_db()

# build a name -> id lookup from the menu
items = get_menu_items()
menu = {row['name'].lower(): row['id'] for row in items}

# make sure newer items exist (in case seed.py wasn't re-run on an old db)
def ensure_item(cat_name, item_name, price, cost):
    if item_name.lower() in menu:
        return
    cats = {c['name']: c['id'] for c in get_menu_categories()}
    cat_id = cats.get(cat_name) or add_menu_category(cat_name)
    iid = add_menu_item(cat_id, item_name, price=price, cost=cost)
    menu[item_name.lower()] = iid
    print(f'Added {item_name} to menu ({cat_name})')

ensure_item('Snacks', 'Egg Puff',      price=3.99,  cost=1.20)
ensure_item('Snacks', 'Paneer Puff',   price=4.49,  cost=1.40)
ensure_item('Momos',  'Momos Fried',   price=8.99,  cost=2.50)
ensure_item('Momos',  'Momos Steamed', price=8.99,  cost=2.40)

# date -> list of (item name, quantity)
historical_orders = {
    '2026-04-09': [
        ('Chicken Fried Rice', 2),
        ('Chicken Noodles', 5),
        ('Double Egg Noodles', 1),
        ('Egg Fried Rice', 1),
        ('Egg Noodles', 1),
        ('Egg Puff', 1),
    ],
    '2026-04-10': [
        ('Chicken Fried Rice', 3),
        ('Chicken Noodles', 1),
        ('Double Egg Fried Rice', 1),
        ('Veg Fried Rice', 2),
        ('Egg Noodles', 2),
        ('Chicken 65', 4),
        ('Veg Noodles', 1),
        ('Paneer Puff', 2),
        ('Momos Fried', 4),
        ('Momos Steamed', 2),
    ],
}

for date, orders in historical_orders.items():
    print(f'\n--- {date} ---')
    for name, qty in orders:
        item_id = menu.get(name.lower())
        if not item_id:
            print(f'  Warning: "{name}" not found in menu, skipping')
            continue
        create_order(
            source='dine-in',
            customer_name='',
            customer_phone='',
            notes='',
            items=[{'menu_item_id': item_id, 'quantity': qty}],
            order_date=date,
        )
        print(f'  {name} x{qty}')

print('\nDone.')
