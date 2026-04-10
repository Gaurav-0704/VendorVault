# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Database

import os
import sqlite3
from flask import g
from config import DATABASE


# ── Connection Helpers ───────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── Schema ───────────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")

    db.executescript('''
        -- ── Business Settings ───────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- ── Purchase Categories (Protein, Veggies, Packaging …) ────────
        CREATE TABLE IF NOT EXISTS purchase_categories (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT '📦'
        );

        -- ── Purchase Items (Chicken, Rice, Oil …) ──────────────────────
        CREATE TABLE IF NOT EXISTS purchase_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id   INTEGER NOT NULL,
            name          TEXT NOT NULL,
            unit          TEXT NOT NULL DEFAULT 'unit',
            quantity      REAL NOT NULL DEFAULT 0,
            price         REAL NOT NULL DEFAULT 0,
            price_per_unit REAL GENERATED ALWAYS AS (
                CASE WHEN quantity > 0 THEN price / quantity ELSE 0 END
            ) STORED,
            notes         TEXT DEFAULT '',
            updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES purchase_categories(id)
        );

        -- ── Menu Categories ────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS menu_categories (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL UNIQUE,
            icon           TEXT DEFAULT '🍽️',
            is_sunday_only INTEGER DEFAULT 0,
            sort_order     INTEGER DEFAULT 0
        );

        -- ── Menu Items ─────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS menu_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id     INTEGER NOT NULL,
            name            TEXT NOT NULL,
            selling_price   REAL NOT NULL DEFAULT 0,
            cost_per_item   REAL NOT NULL DEFAULT 0,
            profit_per_item REAL GENERATED ALWAYS AS (selling_price - cost_per_item) STORED,
            profit_margin   REAL GENERATED ALWAYS AS (
                CASE WHEN selling_price > 0
                     THEN ((selling_price - cost_per_item) / selling_price) * 100
                     ELSE 0 END
            ) STORED,
            is_available    INTEGER DEFAULT 1,
            is_sunday_only  INTEGER DEFAULT 0,
            notes           TEXT DEFAULT '',
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES menu_categories(id)
        );

        -- ── Orders ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number   TEXT NOT NULL UNIQUE,
            customer_name  TEXT DEFAULT 'Walk-in',
            customer_phone TEXT DEFAULT '',
            source         TEXT DEFAULT 'offline',
            status         TEXT DEFAULT 'completed',
            subtotal       REAL NOT NULL DEFAULT 0,
            total_cost     REAL NOT NULL DEFAULT 0,
            profit         REAL NOT NULL DEFAULT 0,
            notes          TEXT DEFAULT '',
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- ── Order Line Items ───────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS order_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            item_name    TEXT NOT NULL,
            quantity     INTEGER NOT NULL DEFAULT 1,
            unit_price   REAL NOT NULL DEFAULT 0,
            unit_cost    REAL NOT NULL DEFAULT 0,
            total_price  REAL NOT NULL DEFAULT 0,
            total_cost   REAL NOT NULL DEFAULT 0,
            profit       REAL NOT NULL DEFAULT 0,
            extras       TEXT DEFAULT '{}',
            FOREIGN KEY (order_id)     REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        );

        -- ── Expenses (rent, gas, marketing …) ─────────────────────────
        CREATE TABLE IF NOT EXISTS expenses (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            category     TEXT NOT NULL DEFAULT 'other',
            description  TEXT NOT NULL,
            amount       REAL NOT NULL DEFAULT 0,
            date         TEXT NOT NULL,
            is_recurring INTEGER DEFAULT 0,
            recurrence   TEXT DEFAULT '',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- ── WhatsApp Config ────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS whatsapp_config (
            id             INTEGER PRIMARY KEY DEFAULT 1,
            phone_number   TEXT DEFAULT '',
            api_token      TEXT DEFAULT '',
            webhook_secret TEXT DEFAULT '',
            is_enabled     INTEGER DEFAULT 0,
            auto_confirm   INTEGER DEFAULT 0,
            updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- ── WhatsApp Message Log ───────────────────────────────────────
        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id    TEXT DEFAULT '',
            from_number   TEXT NOT NULL,
            message_text  TEXT NOT NULL,
            parsed_order  TEXT DEFAULT '{}',
            is_processed  INTEGER DEFAULT 0,
            order_id      INTEGER DEFAULT NULL,
            received_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );
    ''')

    db.commit()
    db.close()


# ── Seed Data ────────────────────────────────────────────────────────────────

def seed_default_data():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    # Skip if already seeded
    if db.execute("SELECT COUNT(*) FROM purchase_categories").fetchone()[0] > 0:
        db.close()
        return

    # ── Purchase Categories ──────────────────────────────────────────────
    categories = [
        ('Protein', '🍗'),  ('Eggs', '🥚'),      ('Grains', '🍚'),
        ('Noodles', '🍜'),  ('Oil', '🛢️'),       ('Veggies & Sauces', '🥬'),
        ('Packaging', '📦'), ('Spices', '🧂'),
    ]
    for name, icon in categories:
        db.execute("INSERT INTO purchase_categories (name, icon) VALUES (?, ?)",
                   (name, icon))

    # ── Purchase Items (your actual costs) ───────────────────────────────
    purchase_items = [
        ('Protein',         'Chicken',              'lbs',     40,  82.40,
         '70g per noodles/rice, 200g per C65'),
        ('Eggs',            'Eggs',                 'dozen',   12,  22.00,
         '12 doz x 12 = 144 eggs. 2/plate, 3 for double egg.'),
        ('Grains',          'Rice',                 'lbs',     20,  22.00,
         '1 cup (~150g) per plate'),
        ('Noodles',         'Noodle Packets',       'packets',  1,   6.00,
         '1 packet = 4 plates'),
        ('Oil',             'Cooking Oil',          'gallon',   1,   9.00,
         '~half gallon used per batch'),
        ('Veggies & Sauces','Mixed Veggies & Sauces','batch',  1,  50.00,
         'Estimated $1-2 per plate'),
        ('Packaging',       'Containers (150ct)',   'pack',     1,  16.50,
         '$0.11 per order'),
        ('Packaging',       'Spoons (250ct)',       'pack',     1,  12.50,
         '$0.05 per order'),
        ('Packaging',       'Plastic Bags (500ct)', 'pack',     1,  28.00,
         '$0.056 per order'),
    ]
    for cat_name, name, unit, qty, price, notes in purchase_items:
        cat_id = db.execute(
            "SELECT id FROM purchase_categories WHERE name=?", (cat_name,)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO purchase_items "
            "(category_id, name, unit, quantity, price, notes) "
            "VALUES (?,?,?,?,?,?)",
            (cat_id, name, unit, qty, price, notes),
        )

    # ── Menu Categories ──────────────────────────────────────────────────
    menu_cats = [
        ('Noodles',         '🍜', 0, 1),
        ('Fried Rice',      '🍚', 0, 2),
        ('Chicken',         '🍗', 0, 3),
        ('Sunday Specials', '🌟', 1, 4),
    ]
    for name, icon, is_sunday, sort in menu_cats:
        db.execute(
            "INSERT INTO menu_categories "
            "(name, icon, is_sunday_only, sort_order) VALUES (?,?,?,?)",
            (name, icon, is_sunday, sort),
        )

    # ── Menu Items with cost calculations ────────────────────────────────
    #   Packaging : $0.22 per order
    #   Veggies   : ~$1.50 avg per plate
    #   Oil       : ~$0.30 per plate
    #   Chicken   : $82.40 / (40 lbs × 453.592 g) ≈ $0.00454/g
    #       70 g  → $0.318    200 g → $0.908
    #   Eggs      : $22 / 144 ≈ $0.153 each
    #       ×2 → $0.306      ×3 → $0.459
    #   Rice      : $22 / 20 lbs → 150 g cup ≈ $0.363
    #   Noodles   : $6 / 4 plates = $1.50

    pkg = 0.22;  veg = 1.50;  oil = 0.30
    c70 = 0.318; c200 = 0.908
    e2 = 0.306;  e3 = 0.459
    rice = 0.363; noodle = 1.50

    menu_items = [
        # (category, name, selling_price, cost)
        ('Noodles',    'Veg Noodles',           9.99,  noodle + veg + oil + pkg),
        ('Noodles',    'Egg Noodles',          10.99,  noodle + veg + oil + e2 + pkg),
        ('Noodles',    'Double Egg Noodles',   11.99,  noodle + veg + oil + e3 + pkg),
        ('Noodles',    'Chicken Noodles',      12.99,  noodle + veg + oil + c70 + pkg),
        ('Fried Rice', 'Veg Fried Rice',        9.99,  rice + veg + oil + pkg),
        ('Fried Rice', 'Egg Fried Rice',       10.99,  rice + veg + oil + e2 + pkg),
        ('Fried Rice', 'Double Egg Fried Rice',11.99,  rice + veg + oil + e3 + pkg),
        ('Fried Rice', 'Chicken Fried Rice',   12.99,  rice + veg + oil + c70 + pkg),
        ('Chicken',    'Chicken 65',            9.99,  c200 + veg + oil + pkg),
    ]
    for cat_name, name, price, cost in menu_items:
        cat_id = db.execute(
            "SELECT id FROM menu_categories WHERE name=?", (cat_name,)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO menu_items "
            "(category_id, name, selling_price, cost_per_item, is_sunday_only) "
            "VALUES (?,?,?,?,0)",
            (cat_id, name, price, round(cost, 2)),
        )

    # ── Default Settings ─────────────────────────────────────────────────
    for key, value in [
        ('business_name', 'My Cloud Kitchen'),
        ('business_type', 'cloud_kitchen'),
        ('currency',      'USD'),
        ('currency_symbol','$'),
        ('tax_rate',      '0'),
        ('timezone',      'America/New_York'),
    ]:
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
                   (key, value))

    db.execute(
        "INSERT OR IGNORE INTO whatsapp_config (id, phone_number) "
        "VALUES (1, '+19373969861')"
    )

    db.commit()
    db.close()
    print("  ✅ Database seeded with your business data!")
