# Gaurav Singh Thakur — MIT License
#
# I call init_db() once at startup. It creates every table the app needs
# and won't touch anything if the tables already exist.

from db.connection import _connect


def init_db():
    with _connect() as conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS menu_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES menu_categories(id) ON DELETE CASCADE)''')

        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL DEFAULT 'dine-in',
            customer_name TEXT,
            customer_phone TEXT,
            notes TEXT,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id))''')

        c.execute('''CREATE TABLE IF NOT EXISTS purchase_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            emoji TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT,
            price REAL NOT NULL,
            notes TEXT,
            purchase_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES purchase_categories(id) ON DELETE CASCADE)''')

        # migration guard for older databases that didn't have this column
        cols = [row[1] for row in c.execute('PRAGMA table_info(purchase_items)').fetchall()]
        if 'purchase_date' not in cols:
            c.execute('ALTER TABLE purchase_items ADD COLUMN purchase_date TEXT')

        c.execute('''CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS stock_levels (
            category_id INTEGER PRIMARY KEY,
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT,
            item_name TEXT,
            last_updated TEXT,
            FOREIGN KEY (category_id) REFERENCES purchase_categories(id) ON DELETE CASCADE)''')

        c.execute('''CREATE TABLE IF NOT EXISTS weekly_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            starting_cash REAL NOT NULL DEFAULT 400,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS whatsapp_config (
            id INTEGER PRIMARY KEY,
            phone_number_id TEXT,
            business_account_id TEXT,
            access_token TEXT,
            verify_token TEXT,
            enabled INTEGER DEFAULT 0)''')

        c.execute('''CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT,
            parsed_order TEXT,
            status TEXT DEFAULT 'received',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        defaults = [
            ('business_name', 'My Restaurant'),
            ('phone', ''),
            ('email', ''),
            ('address', ''),
            ('currency', 'USD'),
            ('cash_in_hand', '867'),
            ('weekly_start_amount', '400'),
        ]
        for key, val in defaults:
            c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))
