# Gaurav Singh Thakur — MIT License
#
# Main entry point. I register all the blueprints here and handle a few
# top-level routes that didn't fit cleanly into any one blueprint.
# Run with: python app.py

import os
import socket
import hmac
from flask import Flask, render_template, request, jsonify, session, redirect, Response

from routes.whatsapp import whatsapp_bp
from routes.ai import ai_bp
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
app.register_blueprint(whatsapp_bp)
app.register_blueprint(ai_bp)

# Safety net: make sure the tables exist as soon as the app is imported.
# In a fresh deploy the container might import the app before seeding runs, so
# without this the first request could 500. init_db() is idempotent
# (CREATE TABLE IF NOT EXISTS), so calling it here is cheap and safe.
try:
    init_db()
except Exception as _e:
    print(f'init_db() at import failed (will retry on first request): {_e}')


# ============================================================================
# Authentication
# ============================================================================
# Single owner login. I keep it deliberately simple — one account, a signed
# session cookie, no database user table. Credentials come from env vars so
# nothing sensitive lives in the repo.

app.secret_key = os.environ.get('APP_SECRET_KEY', 'dev-secret-change-me-in-production')
OWNER_USERNAME = os.environ.get('APP_USERNAME', 'owner')
OWNER_PASSWORD = os.environ.get('APP_PASSWORD', 'vendorvault')

# Paths that don't need a login: the health check (Railway pings this),
# the login/logout routes themselves, the PWA manifest, and static assets.
_PUBLIC_EXACT = {'/health', '/login', '/logout', '/manifest.json', '/sw.js', '/favicon.ico'}
_PUBLIC_PREFIX = ('/static/',)


def _is_public(path):
    return path in _PUBLIC_EXACT or path.startswith(_PUBLIC_PREFIX)


@app.before_request
def require_login():
    if _is_public(request.path):
        return
    if session.get('auth'):
        return
    # Not logged in — API calls get a clean 401, page loads bounce to /login
    if request.path.startswith('/api/'):
        return jsonify({'error': 'authentication required'}), 401
    return redirect('/login')


_LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VendorVault — Sign in</title>
<style>
  * { box-sizing: border-box; }
  html, body { height:100%; }
  body {
    margin:0; min-height:100vh; overflow:hidden;
    display:flex; align-items:center; justify-content:center;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    color:#f1f5f9; background:#05070f;
    perspective:1400px;
  }

  /* Animated aurora background */
  .bg { position:fixed; inset:0; overflow:hidden; z-index:0; }
  .blob { position:absolute; border-radius:50%; filter:blur(70px); opacity:0.55;
    mix-blend-mode:screen; will-change:transform; }
  .blob.a { width:520px; height:520px; top:-140px; left:-120px;
    background:radial-gradient(circle at 30% 30%, #6366f1, transparent 70%);
    animation:drift1 18s ease-in-out infinite; }
  .blob.b { width:460px; height:460px; bottom:-160px; right:-100px;
    background:radial-gradient(circle at 30% 30%, #22d3ee, transparent 70%);
    animation:drift2 22s ease-in-out infinite; }
  .blob.c { width:400px; height:400px; top:40%; left:55%;
    background:radial-gradient(circle at 30% 30%, #a855f7, transparent 70%);
    animation:drift3 26s ease-in-out infinite; }
  /* faint moving grid for depth */
  .grid { position:fixed; inset:0; z-index:0; opacity:0.06;
    background-image:linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg,#fff 1px, transparent 1px);
    background-size:44px 44px; mask-image:radial-gradient(circle at 50% 40%, #000 0%, transparent 75%);
    -webkit-mask-image:radial-gradient(circle at 50% 40%, #000 0%, transparent 75%);
    animation:gridpan 40s linear infinite; }

  @keyframes drift1 { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(80px,60px) scale(1.15)} }
  @keyframes drift2 { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(-70px,-50px) scale(1.1)} }
  @keyframes drift3 { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(-60px,70px) scale(1.2)} }
  @keyframes gridpan { from{background-position:0 0,0 0} to{background-position:44px 44px,44px 44px} }
  @keyframes rise { from{opacity:0; transform:rotateX(10deg) translateY(24px)} to{opacity:1; transform:rotateX(0) translateY(0)} }
  @keyframes floaty { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }

  /* 3D glass card */
  .box {
    position:relative; z-index:2; width:100%; max-width:380px; padding:34px 30px;
    background:linear-gradient(160deg, rgba(23,30,52,0.72), rgba(12,16,30,0.72));
    border:1px solid rgba(148,163,184,0.18); border-radius:22px;
    backdrop-filter:blur(22px) saturate(140%); -webkit-backdrop-filter:blur(22px) saturate(140%);
    box-shadow:0 30px 80px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.08);
    transform-style:preserve-3d;
    animation:rise 0.7s cubic-bezier(0.2,0.8,0.2,1) both, floaty 7s ease-in-out 0.7s infinite;
  }
  .box::before { content:""; position:absolute; inset:0; border-radius:22px; padding:1px;
    background:linear-gradient(140deg, rgba(129,140,248,0.6), transparent 40%, rgba(34,211,238,0.4));
    -webkit-mask:linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite:xor; mask-composite:exclude; pointer-events:none; }

  .logo { width:46px; height:46px; border-radius:13px; display:flex; align-items:center; justify-content:center;
    font-size:24px; margin-bottom:14px;
    background:linear-gradient(135deg,#6366f1,#22d3ee); box-shadow:0 8px 24px rgba(99,102,241,0.45);
    transform:translateZ(40px); }
  .brand { font-size:29px; font-weight:800; letter-spacing:-0.6px; margin-bottom:4px;
    background:linear-gradient(120deg,#c7d2fe,#818cf8 40%,#67e8f9); -webkit-background-clip:text;
    background-clip:text; color:transparent; transform:translateZ(30px); }
  .sub { color:#94a3b8; font-size:14px; margin-bottom:22px; transform:translateZ(20px); }

  label { display:block; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;
    color:#8b98b0; margin-bottom:7px; margin-top:16px; }
  input { width:100%; padding:13px 15px; background:rgba(5,7,15,0.6);
    border:1px solid rgba(148,163,184,0.18); border-radius:12px; color:#f1f5f9; font-size:15px;
    transition:border-color .2s, box-shadow .2s, background .2s; }
  input:focus { outline:none; border-color:#818cf8; background:rgba(5,7,15,0.85);
    box-shadow:0 0 0 4px rgba(129,140,248,0.18); }

  button { width:100%; margin-top:26px; padding:14px; color:#fff; border:none; border-radius:12px;
    font-size:15px; font-weight:700; cursor:pointer; letter-spacing:0.2px;
    background:linear-gradient(135deg,#6366f1,#4f46e5); box-shadow:0 10px 26px rgba(79,70,229,0.5);
    transition:transform .15s ease, box-shadow .15s ease, filter .15s ease; transform:translateZ(20px); }
  button:hover { transform:translateZ(20px) translateY(-2px); box-shadow:0 16px 34px rgba(79,70,229,0.6); filter:brightness(1.07); }
  button:active { transform:translateZ(20px) translateY(0); }

  .err { margin-top:16px; padding:10px 12px; background:rgba(248,113,113,0.12);
    border:1px solid rgba(248,113,113,0.35); border-radius:10px; color:#fca5a5; font-size:13px; }
  .demo { margin-bottom:20px; padding:13px 15px; border-radius:13px; font-size:13px; color:#c7d2fe;
    background:linear-gradient(135deg, rgba(129,140,248,0.16), rgba(34,211,238,0.08));
    border:1px solid rgba(129,140,248,0.32); }
  .demo b { color:#fff; }
  .demo-title { display:flex; align-items:center; gap:6px; font-weight:700; color:#a5b4fc; margin-bottom:5px; }
  .foot { margin-top:20px; text-align:center; font-size:12px; color:#64748b; transform:translateZ(10px); }

  @media (prefers-reduced-motion: reduce) {
    .blob, .grid, .box { animation:none !important; }
  }
  @media (max-width:440px) { .box { max-width:92vw; padding:28px 22px; } }
</style></head>
<body>
  <div class="bg"><div class="blob a"></div><div class="blob b"></div><div class="blob c"></div></div>
  <div class="grid"></div>
  <form class="box" method="post" action="/login">
    <div class="logo">🍳</div>
    <div class="brand">VendorVault</div>
    <div class="sub">Sign in to your kitchen dashboard</div>
    {demo}
    {error}
    <label>Username</label>
    <input name="username" autocomplete="username" value="{user_val}" autofocus>
    <label>Password</label>
    <input name="password" type="password" autocomplete="current-password" value="{pw_val}">
    <button type="submit">Sign in →</button>
    <div class="foot">Restaurant management, WhatsApp-first.</div>
  </form>
</body></html>"""


def _render_login(error=''):
    """Builds the login page with a demo-credentials box and the fields pre-filled,
    so anyone opening the live link can just click Sign in."""
    demo = (
        '<div class="demo"><span class="demo-title">✦ Demo login</span>'
        f'Username <b>{OWNER_USERNAME}</b> &nbsp;·&nbsp; Password <b>{OWNER_PASSWORD}</b><br>'
        'Already filled in — just hit Sign in.</div>'
    )
    return (_LOGIN_PAGE
            .replace('{demo}', demo)
            .replace('{error}', error)
            .replace('{user_val}', OWNER_USERNAME)
            .replace('{pw_val}', OWNER_PASSWORD))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('auth'):
        return redirect('/')
    if request.method == 'POST':
        user = request.form.get('username', '')
        pw = request.form.get('password', '')
        # constant-time compare so login timing can't leak the credentials
        ok = hmac.compare_digest(user, OWNER_USERNAME) and hmac.compare_digest(pw, OWNER_PASSWORD)
        if ok:
            session['auth'] = True
            session.permanent = True
            return redirect('/')
        err = '<div class="err">Wrong username or password.</div>'
        return Response(_render_login(err), mimetype='text/html'), 401
    return Response(_render_login(), mimetype='text/html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/health')
def health():
    # Public, unauthenticated — this is what Railway's health check hits.
    return jsonify({'status': 'ok'})


@app.after_request
def prevent_caching(response):
    # I don't want the browser serving stale API data
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response


# ============================================================================
# Pages
# ============================================================================

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
    return '// VendorVault service worker stub', 200, {
        'Content-Type': 'application/javascript'
    }


# ============================================================================
# Dashboard
# ============================================================================

@app.route('/api/dashboard')
def dashboard():
    return jsonify(get_dashboard_stats())


# ============================================================================
# Orders
# ============================================================================

@app.route('/api/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        try:
            data = request.get_json()
            # I accept both camelCase (frontend) and snake_case (direct API calls)
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


# ============================================================================
# Menu
# ============================================================================

@app.route('/api/menu')
def menu():
    return jsonify(get_menu_with_categories())


@app.route('/api/menu/categories', methods=['POST'])
def create_menu_cat():
    try:
        data = request.get_json()
        category_id = add_menu_category(data['name'])
        return jsonify({'id': category_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/categories/<int:category_id>', methods=['DELETE'])
def remove_menu_cat(category_id):
    try:
        delete_menu_category(category_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/menu/items', methods=['POST'])
def create_menu_item_route():
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
    if request.method == 'DELETE':
        try:
            delete_menu_item(item_id)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    try:
        data = request.get_json()
        update_menu_item(item_id, name=data.get('name'), price=data.get('price'), cost=data.get('cost'))
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


# ============================================================================
# Purchases
# ============================================================================

@app.route('/api/purchases')
def purchases():
    return jsonify(get_purchases_with_categories())


@app.route('/api/purchases/categories', methods=['POST'])
def create_purchase_cat():
    try:
        data = request.get_json()
        category_id = add_purchase_category(data['name'], data.get('emoji'))
        return jsonify({'id': category_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/categories/<int:category_id>', methods=['DELETE'])
def remove_purchase_cat(category_id):
    try:
        delete_purchase_category(category_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases/items', methods=['POST'])
def create_purchase_item_route():
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
    daily_date = request.args.get('daily_date')
    weekly_start = request.args.get('weekly_start')
    weekly_end = request.args.get('weekly_end')
    month = request.args.get('month')

    daily = get_daily_report(daily_date)
    weekly = get_weekly_report(weekly_start, weekly_end) if weekly_start and weekly_end else get_weekly_report()
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


# ============================================================================
# Profits and Cost Analysis
# ============================================================================

@app.route('/api/profits')
def profits():
    return jsonify(get_profits_data())


@app.route('/api/cost-analysis')
def cost_analysis():
    return jsonify(get_cost_analysis())


# ============================================================================
# Expenses / Payouts
# ============================================================================

@app.route('/api/expenses', methods=['GET', 'POST'])
def expenses():
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
    return jsonify(get_stock_levels())


# ============================================================================
# Finance
# ============================================================================

@app.route('/api/finance')
def finance():
    return jsonify(get_finance_summary())


@app.route('/api/finance/weekly-cycle')
def weekly_cycle():
    return jsonify(get_weekly_cycle_data())


@app.route('/api/finance/end-of-day')
def end_of_day():
    date = request.args.get('date')
    return jsonify(get_end_of_day_report(date))


@app.route('/api/finance/cash', methods=['PUT'])
def update_cash():
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
    if request.method == 'GET':
        data = get_all_settings()
        # Never expose the raw AI key — only whether one is set, plus a masked hint
        raw_key = data.pop('ai_api_key', '')
        if raw_key:
            data['ai_key_set'] = True
            data['ai_key_preview'] = '••••••••' + raw_key[-4:]
        else:
            data['ai_key_set'] = False
            data['ai_key_preview'] = ''
        return jsonify(data)
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


@app.route('/api/settings/ai-key', methods=['PUT'])
def set_ai_key():
    """Save the owner's Anthropic API key. Stored in settings like everything else."""
    data = request.get_json() or {}
    key = (data.get('key') or '').strip()
    if not key:
        return jsonify({'error': 'API key cannot be empty'}), 400
    set_setting('ai_api_key', key)
    return jsonify({'success': True, 'preview': '••••••••' + key[-4:]})


@app.route('/api/settings/ai-key', methods=['DELETE'])
def delete_ai_key():
    """Remove the AI key. AI features switch off; everything else keeps working."""
    set_setting('ai_api_key', '')
    return jsonify({'success': True})


# ============================================================================
# Network Info
# ============================================================================

@app.route('/api/network-info')
def network_info():
    # I use this to get my local IP so I can open the app on my phone
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
# Start
# ============================================================================

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    print(f'VendorVault running on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
