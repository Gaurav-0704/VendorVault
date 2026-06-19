# Gaurav Singh Thakur — MIT License

from db.connection import _connect


def add_menu_category(name):
    with _connect() as conn:
        c = conn.execute('INSERT INTO menu_categories (name) VALUES (?)', (name,))
        return c.lastrowid


def get_menu_categories():
    with _connect() as conn:
        return [dict(r) for r in conn.execute(
            'SELECT id, name, created_at FROM menu_categories ORDER BY name'
        ).fetchall()]


def delete_menu_category(category_id):
    with _connect() as conn:
        conn.execute('DELETE FROM menu_categories WHERE id = ?', (category_id,))


def add_menu_item(category_id, name, price, cost):
    with _connect() as conn:
        c = conn.execute(
            'INSERT INTO menu_items (category_id, name, price, cost) VALUES (?, ?, ?, ?)',
            (category_id, name, float(price), float(cost)),
        )
        return c.lastrowid


def get_menu_items(category_id=None):
    with _connect() as conn:
        if category_id:
            rows = conn.execute(
                'SELECT id, category_id, name, price, cost FROM menu_items WHERE category_id = ? ORDER BY name',
                (category_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT id, category_id, name, price, cost FROM menu_items ORDER BY name'
            ).fetchall()
        return [dict(r) for r in rows]


def get_menu_item(item_id):
    with _connect() as conn:
        row = conn.execute(
            'SELECT id, category_id, name, price, cost FROM menu_items WHERE id = ?', (item_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_menu_item(item_id):
    with _connect() as conn:
        conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))


def update_menu_item(item_id, name=None, price=None, cost=None):
    with _connect() as conn:
        current = conn.execute(
            'SELECT id, name, price, cost FROM menu_items WHERE id = ?', (item_id,)
        ).fetchone()
        if not current:
            return False
        current = dict(current)
        c = conn.execute(
            'UPDATE menu_items SET name = ?, price = ?, cost = ? WHERE id = ?',
            (name or current['name'],
             float(price) if price is not None else current['price'],
             float(cost) if cost is not None else current['cost'],
             item_id),
        )
        return c.rowcount > 0


def get_menu_with_categories():
    """Builds the nested structure the frontend expects — categories with their items inside."""
    cats = get_menu_categories()
    for cat in cats:
        cat['items'] = get_menu_items(cat['id'])
    return cats
