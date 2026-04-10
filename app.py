import os
import sys
import socket
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

from database import (
    init_db,
    get_dashboard_stats,
    get_orders, create_order, delete_order,
    get_menu_with_categories, get_menu_items,
    add_menu_category, delete_menu_category,
    add_menu_item, delete_menu_item,
    get_purchases_with_categories,
    add_purchase_category, delete_purchase_category,
    add_purchase_item, delete_purchase_item,
    get_daily_report, get_weekly_report, get_monthly_report,
    get_all_settings, set_setting,
    get_profits_data, get_cost_analysis,
)

app = Flask(__name__, template_folder='.', static_folder='.')


# pages

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/manifest.json')
def manifest():
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
    return '// no-op service worker', 200, {'Content-Type': 'application/javascript'}


# dashboard

@app.route('/api/dashboard')
def dashboard():
    return jsonify(get_dashboard_stats())


# orders

@app.route('/api/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        try:
            data = request.get_json()

            # frontend sends camelCase, direct API calls might use snake_case
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
            )
            return jsonify({'id': order_id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # list orders
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
    try:
        delete_order(order_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# menu

@app.route('/api/menu')
def menu():
    return jsonify(get_menu_with_categories())


@app.route('/api/menu/categories', methods=['POST'])
def create_menu_category():
    try:
        data = request.get_json()
        cid = add_menu_category(data['name'])
        return jsonify({'id': cid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/categories/<int:cid>', methods=['DELETE'])
def remove_menu_category(cid):
    try:
        delete_menu_category(cid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/items', methods=['POST'])
def create_menu_item():
    try:
        data = request.get_json()
        iid = add_menu_item(
            data.get('category_id') or data.get('categoryId'),
            data['name'],
            data['price'],
            data['cost'],
        )
        return jsonify({'id': iid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/items/<int:iid>', methods=['DELETE'])
def remove_menu_item(iid):
    try:
        delete_menu_item(iid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/cost-breakdown')
def cost_breakdown():
    items = get_menu_items()
    breakdown = []
    for item in items:
        margin = 0
        if item['price'] and item['price'] > 0:
            margin = round(((item['price'] - item['cost']) / item['price']) * 100, 1)
        breakdown.append({
            'name': item['name'],
            'price': item['price'],
            'cost': item['cost'],
            'margin': margin,
        })
    return jsonify({'menu_items': breakdown})


# purchases

@app.route('/api/purchases')
def purchases():
    return jsonify(get_purchases_with_categories())


@app.route('/api/purchases/categories', methods=['POST'])
def create_purchase_category():
    try:
        data = request.get_json()
        cid = add_purchase_category(data['name'], data.get('emoji'))
        return jsonify({'id': cid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/categories/<int:cid>', methods=['DELETE'])
def remove_purchase_category(cid):
    try:
        delete_purchase_category(cid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/items', methods=['POST'])
def create_purchase_item():
    try:
        data = request.get_json()
        iid = add_purchase_item(
            category_id=data.get('category_id') or data.get('categoryId'),
            name=data['name'],
            quantity=data['quantity'],
            unit=data.get('unit', 'pcs'),
            price=data['price'],
            notes=data.get('notes', ''),
        )
        return jsonify({'id': iid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/items/<int:iid>', methods=['DELETE'])
def remove_purchase_item(iid):
    try:
        delete_purchase_item(iid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# reports

@app.route('/api/reports')
def combined_reports():
    daily = get_daily_report()
    weekly = get_weekly_report()
    monthly = get_monthly_report()

    return jsonify({
        'daily': {
            'revenue': daily['revenue'],
            'orders': daily['orders'],
            'breakdown': daily.get('items', []),
        },
        'weekly': {
            'revenue': weekly['revenue'],
            'orders': weekly['orders'],
            'breakdown': weekly.get('daily', []),
        },
        'monthly': {
            'revenue': monthly['revenue'],
            'orders': monthly['orders'],
            'breakdown': monthly.get('weekly', []),
        },
    })


@app.route('/api/reports/daily')
def daily_report():
    date = request.args.get('date')
    return jsonify(get_daily_report(date))


@app.route('/api/reports/weekly')
def weekly_report():
    start = request.args.get('start')
    end = request.args.get('end')
    return jsonify(get_weekly_report(start, end))


@app.route('/api/reports/monthly')
def monthly_report():
    month = request.args.get('month')
    return jsonify(get_monthly_report(month))


# profits

@app.route('/api/profits')
def profits():
    return jsonify(get_profits_data())


# cost analysis

@app.route('/api/cost-analysis')
def cost_analysis():
    return jsonify(get_cost_analysis())


# settings

@app.route('/api/settings', methods=['GET', 'PUT'])
def settings():
    if request.method == 'GET':
        return jsonify(get_all_settings())

    try:
        data = request.get_json()
        for key, value in data.items():
            set_setting(key, value)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# network

@app.route('/api/network-info')
def network_info():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        port = int(os.environ.get('PORT', 5000))
        return jsonify({
            'ip': local_ip,
            'port': port,
            'localUrl': f'http://localhost:{port}',
            'networkUrl': f'http://{local_ip}:{port}',
        })
    except socket.error:
        return jsonify({'error': 'Could not determine network info'}), 500


# errors

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# run

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    print(f'VendorVault running on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
