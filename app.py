# VendorVault - Restaurant Management System
# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
#
# Flask server handling all API routes and page rendering.
# Run with: python app.py

import os
import socket
from flask import Flask, render_template, request, jsonify

from database import (
    init_db,
    get_dashboard_stats,
    get_orders, create_order, delete_order,
    get_menu_with_categories, get_menu_items,
    add_menu_category, delete_menu_category,
    add_menu_item, delete_menu_item, update_menu_item,
    get_purchases_with_categories,
    add_purchase_category, delete_purchase_category,
    add_purchase_item, add_purchase_items_bulk, delete_purchase_item,
    get_daily_report, get_weekly_report, get_monthly_report,
    get_all_settings, set_setting,
    get_profits_data, get_cost_analysis,
    add_expense, get_expenses, delete_expense,
    update_stock, get_stock_levels, get_finance_summary,
    get_weekly_cycle_data, get_end_of_day_report, update_cash_in_hand,
)


app = Flask(__name__, template_folder='.', static_folder='.')


@app.after_request
def prevent_caching(response):
    """Prevent browsers from caching API responses so data is always fresh."""
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response


# ============================================================================
# Pages
# ============================================================================

@app.route('/')
def index():
    """Render the main single-page application."""
    return render_template('index.html')


@app.route('/manifest.json')
def manifest():
    """Progressive Web App manifest for mobile home screen install."""
    return jsonify({
        'name': 'VendorVault',
        'short_name': 'VendorVault',
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#0f172a',
        'theme_color': '#6366f1',
        'orientation': 'portrait-primary',
        'icons': [],
    })


@app.route('/sw.js')
def service_worker():
    """Stub service worker for PWA compatibility."""
    return '// VendorVault service worker stub', 200, {
        'Content-Type': 'application/javascript'
    }


# ============================================================================
# Dashboard
# ============================================================================

@app.route('/api/dashboard')
def dashboard():
    """Get today's stats, recent orders, hourly breakdown, and top items."""
    return jsonify(get_dashboard_stats())


# ============================================================================
# Orders
# ============================================================================

@app.route('/api/orders', methods=['GET', 'POST'])
def orders():
    """List all orders (GET) or place a new order (POST)."""
    if request.method == 'POST':
        try:
            data = request.get_json()

            # Accept both camelCase (frontend) and snake_case (API) field names
            items = []
            for item in data.get('items', []):
                items.append({
                    'menu_item_id': item.get('menu_item_id') or item.get('itemId'),
                    'quantity': item.get('quantity', 1),
                })

            order_id = create_order(
                source=data.get('source', 'dine-in'),
                customer_name=data.get('customer_name') or data.get('customerName', ''),
                customer_phone=data.get('customer_phone') or data.get('customerPhone', ''),
                notes=data.get('notes') or data.get('note', ''),
                items=items,
                order_date=data.get('order_date') or data.get('orderDate'),
            )
            return jsonify({'id': order_id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # GET: return all orders with camelCase keys for the frontend
    raw = get_orders()
    result = []
    for o in raw:
        result.append({
            'id': o['id'],
            'orderNumber': o['order_number'],
            'source': o['source'],
            'customerName': o['customer_name'] or 'Walk-in',
            'customerPhone': o['customer_phone'] or '',
            'notes': o['notes'] or '',
            'status': o['status'],
            'total': o['subtotal'],
            'cost': o['total_cost'],
            'profit': o['profit'],
            'items': o['items'],
            'createdAt': o['created_at'],
        })
    return jsonify(result)


@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def remove_order(order_id):
    """Delete a single order and all its line items."""
    try:
        delete_order(order_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Menu
# ============================================================================

@app.route('/api/menu')
def menu():
    """Get the full menu grouped by category."""
    return jsonify(get_menu_with_categories())


@app.route('/api/menu/categories', methods=['POST'])
def create_menu_cat():
    """Add a new menu category (e.g. Noodles, Fried Rice)."""
    try:
        data = request.get_json()
        category_id = add_menu_category(data['name'])
        return jsonify({'id': category_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/categories/<int:category_id>', methods=['DELETE'])
def remove_menu_cat(category_id):
    """Delete a menu category and all items in it."""
    try:
        delete_menu_category(category_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/items', methods=['POST'])
def create_menu_item_route():
    """Add a new menu item to a category."""
    try:
        data = request.get_json()
        item_id = add_menu_item(
            data.get('category_id') or data.get('categoryId'),
            data['name'],
            data['price'],
            data['cost'],
        )
        return jsonify({'id': item_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/items/<int:item_id>', methods=['DELETE', 'PUT'])
def manage_menu_item(item_id):
    """Delete (DELETE) or update (PUT) a menu item's name, price, or cost."""
    if request.method == 'DELETE':
        try:
            delete_menu_item(item_id)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    try:
        data = request.get_json()
        update_menu_item(
            item_id,
            name=data.get('name'),
            price=data.get('price'),
            cost=data.get('cost'),
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/cost-breakdown')
def cost_breakdown():
    """Get profit margin breakdown for each menu item."""
    items = get_menu_items()
    breakdown = []
    for item in items:
        margin = 0
        if item['price'] and item['price'] > 0:
            margin = round(
                ((item['price'] - item['cost']) / item['price']) * 100, 1
            )
        breakdown.append({
            'name': item['name'],
            'price': item['price'],
            'cost': item['cost'],
            'margin': margin,
        })
    return jsonify({'menu_items': breakdown})


# ============================================================================
# Purchases
# ============================================================================

@app.route('/api/purchases')
def purchases():
    """Get all purchase categories with their items."""
    return jsonify(get_purchases_with_categories())


@app.route('/api/purchases/categories', methods=['POST'])
def create_purchase_cat():
    """Add a new purchase category (e.g. Chicken, Rice)."""
    try:
        data = request.get_json()
        category_id = add_purchase_category(data['name'], data.get('emoji'))
        return jsonify({'id': category_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/categories/<int:category_id>', methods=['DELETE'])
def remove_purchase_cat(category_id):
    """Delete a purchase category."""
    try:
        delete_purchase_category(category_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/items', methods=['POST'])
def create_purchase_item_route():
    """Record a single purchase (also updates stock for that category)."""
    try:
        data = request.get_json()
        item_id = add_purchase_item(
            category_id=data.get('category_id') or data.get('categoryId'),
            name=data['name'],
            quantity=data['quantity'],
            unit=data.get('unit', 'pcs'),
            price=data['price'],
            notes=data.get('notes', ''),
            purchase_date=data.get('purchase_date') or data.get('purchaseDate'),
        )
        return jsonify({'id': item_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/bulk', methods=['POST'])
def create_purchase_bulk():
    """Record multiple purchases at once (e.g. weekly grocery run)."""
    try:
        data = request.get_json()
        purchase_date = data.get('purchase_date') or data.get('purchaseDate')
        items = data.get('items', [])

        if not items:
            return jsonify({'error': 'No items provided'}), 400

        normalized = []
        for item in items:
            normalized.append({
                'category_id': item.get('category_id') or item.get('categoryId'),
                'name': item['name'],
                'quantity': item['quantity'],
                'unit': item.get('unit', 'pcs'),
                'price': item['price'],
                'notes': item.get('notes', ''),
            })

        ids = add_purchase_items_bulk(normalized, purchase_date=purchase_date)
        return jsonify({'ids': ids, 'count': len(ids)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/items/<int:item_id>', methods=['DELETE'])
def remove_purchase_item_route(item_id):
    """Delete a purchase record."""
    try:
        delete_purchase_item(item_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Reports
# ============================================================================

@app.route('/api/reports')
def combined_reports():
    """Combined daily + weekly + monthly report for the Reports tab."""
    daily_date = request.args.get('daily_date')
    weekly_start = request.args.get('weekly_start')
    weekly_end = request.args.get('weekly_end')
    month = request.args.get('month')

    daily = get_daily_report(daily_date)

    if weekly_start and weekly_end:
        weekly = get_weekly_report(weekly_start, weekly_end)
    else:
        weekly = get_weekly_report()

    monthly = get_monthly_report(month) if month else get_monthly_report()

    return jsonify({
        'daily': {
            'revenue': daily['revenue'],
            'expenses': daily['expenses'],
            'profit': daily['profit'],
            'orders': daily['orders'],
            'breakdown': daily.get('items', []),
        },
        'weekly': {
            'revenue': weekly['revenue'],
            'expenses': weekly['expenses'],
            'profit': weekly['profit'],
            'orders': weekly['orders'],
            'breakdown': weekly.get('daily', []),
        },
        'monthly': {
            'revenue': monthly['revenue'],
            'expenses': monthly['expenses'],
            'profit': monthly['profit'],
            'orders': monthly['orders'],
            'breakdown': monthly.get('weekly', []),
        },
    })


@app.route('/api/reports/daily')
def daily_report():
    """Daily report with revenue, cost, profit, and item breakdown."""
    date = request.args.get('date')
    return jsonify(get_daily_report(date))


@app.route('/api/reports/weekly')
def weekly_report():
    """Weekly report with daily breakdown."""
    start = request.args.get('start')
    end = request.args.get('end')
    return jsonify(get_weekly_report(start, end))


@app.route('/api/reports/monthly')
def monthly_report():
    """Monthly report with weekly breakdown."""
    month = request.args.get('month')
    return jsonify(get_monthly_report(month))


# ============================================================================
# Profits and Cost Analysis
# ============================================================================

@app.route('/api/profits')
def profits():
    """Profit breakdown by product with margins."""
    return jsonify(get_profits_data())


@app.route('/api/cost-analysis')
def cost_analysis():
    """Purchase cost analysis grouped by category."""
    return jsonify(get_cost_analysis())


# ============================================================================
# Expenses (Payouts)
# ============================================================================

@app.route('/api/expenses', methods=['GET', 'POST'])
def expenses():
    """List all payouts (GET) or record a new one (POST)."""
    if request.method == 'POST':
        try:
            data = request.get_json()
            expense_id = add_expense(
                description=data['description'],
                amount=data['amount'],
                expense_date=data.get('expense_date') or data.get('expenseDate'),
            )
            return jsonify({'id': expense_id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify(get_expenses())


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def remove_expense(expense_id):
    """Delete a payout record."""
    try:
        delete_expense(expense_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Stock
# ============================================================================

@app.route('/api/stock')
def stock():
    """Current inventory levels per purchase category."""
    return jsonify(get_stock_levels())


# ============================================================================
# Finance
# ============================================================================

@app.route('/api/finance')
def finance():
    """Full financial summary: revenue, expenses, profit, cash position."""
    return jsonify(get_finance_summary())


@app.route('/api/finance/weekly-cycle')
def weekly_cycle():
    """Weekly cash cycle data (Thu-Sun active, Mon collect excess)."""
    return jsonify(get_weekly_cycle_data())


@app.route('/api/finance/end-of-day')
def end_of_day():
    """End-of-day report: orders, items sold, costs, profit for a given date."""
    date = request.args.get('date')
    return jsonify(get_end_of_day_report(date))


@app.route('/api/finance/cash', methods=['PUT'])
def update_cash():
    """Manually update the cash-in-hand amount."""
    try:
        data = request.get_json()
        update_cash_in_hand(data['amount'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Settings
# ============================================================================

@app.route('/api/settings', methods=['GET', 'PUT'])
def settings():
    """Read (GET) or update (PUT) app settings."""
    if request.method == 'GET':
        return jsonify(get_all_settings())

    allowed_keys = {'business_name', 'phone', 'email', 'address', 'currency',
                     'cash_in_hand', 'weekly_start_amount'}
    try:
        data = request.get_json()
        for key, value in data.items():
            if key in allowed_keys:
                set_setting(key, value)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Network Info
# ============================================================================

@app.route('/api/network-info')
def network_info():
    """Detect local and network URLs for mobile access."""
    port = int(os.environ.get('PORT', 5000))
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'
    return jsonify({
        'ip': local_ip,
        'port': port,
        'localUrl': f'http://localhost:{port}',
        'networkUrl': f'http://{local_ip}:{port}',
    })


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    print(f'VendorVault running on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
