# VendorVault - Restaurant Management System
# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
#
# Run this once to load menu items and purchase categories.
# Usage: python seed.py

from database import (
    init_db, add_menu_category, add_menu_item,
    add_purchase_category, get_menu_categories, get_purchase_categories
)

init_db()

# skip if menu already has data
if get_menu_categories():
    print('Menu already has data, skipping. Delete vendorvault.db to start fresh.')
else:
    # menu categories + items (price = what you sell for, cost = what it costs you)
    noodles = add_menu_category('Noodles')
    add_menu_item(noodles, 'Veg Noodles',         price=9.99,  cost=3.67)
    add_menu_item(noodles, 'Egg Noodles',          price=10.99, cost=3.97)
    add_menu_item(noodles, 'Double Egg Noodles',   price=11.99, cost=4.12)
    add_menu_item(noodles, 'Chicken Noodles',      price=12.99, cost=3.98)

    rice = add_menu_category('Fried Rice')
    add_menu_item(rice, 'Veg Fried Rice',          price=9.99,  cost=2.53)
    add_menu_item(rice, 'Egg Fried Rice',          price=10.99, cost=2.84)
    add_menu_item(rice, 'Double Egg Fried Rice',   price=11.99, cost=2.99)
    add_menu_item(rice, 'Chicken Fried Rice',      price=12.99, cost=2.85)

    chicken = add_menu_category('Chicken')
    add_menu_item(chicken, 'Chicken 65',           price=10.99, cost=2.07)

    snacks = add_menu_category('Snacks')
    add_menu_item(snacks, 'Egg Puff',              price=3.99,  cost=1.20)
    add_menu_item(snacks, 'Paneer Puff',           price=4.49,  cost=1.40)

    momos = add_menu_category('Momos')
    add_menu_item(momos, 'Momos Fried',            price=8.99,  cost=2.50)
    add_menu_item(momos, 'Momos Steamed',          price=8.99,  cost=2.40)

    print('Menu loaded: 6 categories, 13 items')

# purchase categories (pre-made so you just add qty + price when you buy)
if get_purchase_categories():
    print('Purchase categories already exist, skipping.')
else:
    add_purchase_category('Chicken',               emoji='🍗')
    add_purchase_category('Eggs',                  emoji='🥚')
    add_purchase_category('Rice',                  emoji='🍚')
    add_purchase_category('Noodles',               emoji='🍜')
    add_purchase_category('Oil',                   emoji='🛢')
    add_purchase_category('Veggies & Sauces',      emoji='🥬')
    add_purchase_category('Spices',                emoji='🧂')
    add_purchase_category('Containers',            emoji='📦')
    add_purchase_category('Spoons',                emoji='🥄')
    add_purchase_category('Plastic Bags',          emoji='🛍')

    print('Purchase categories loaded: 10 categories')

print('Done. Run: python app.py')
