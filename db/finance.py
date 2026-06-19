from datetime import datetime, timedelta
from db.connection import _connect
from db.reports import _orders_in_range, _revenue_and_cost
from db.settings import set_setting


def update_cash_in_hand(amount):
    set_setting('weekly_start_amount', str(round(float(amount), 2)))


def compute_cash_in_hand():
    """Live cash = weekly_start + cycle_revenue - cycle_purchases - cycle_payouts."""
    now = datetime.now()
    days_since_thu = (now.weekday() - 3) % 7
    this_thursday = (now - timedelta(days=days_since_thu)).strftime('%Y-%m-%d')
    this_sunday = (datetime.strptime(this_thursday, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')
    with _connect() as conn:
        weekly_start = float(conn.execute(
            "SELECT value FROM settings WHERE key = 'weekly_start_amount'"
        ).fetchone()['value'] or 400)
        thu_start = datetime.strptime(this_thursday, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
        sun_end = datetime.strptime(this_sunday, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        cycle_ids = [o['id'] for o in _orders_in_range(conn, thu_start, sun_end)]
        cycle_revenue, _ = _revenue_and_cost(conn, cycle_ids)
        cycle_purchases = conn.execute(
            "SELECT COALESCE(SUM(price), 0) as total FROM purchase_items "
            "WHERE purchase_date >= ? AND purchase_date <= ?",
            (this_thursday, this_sunday),
        ).fetchone()['total']
        cycle_payouts = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
            "WHERE expense_date >= ? AND expense_date <= ?",
            (this_thursday, this_sunday),
        ).fetchone()['total']
        return round(weekly_start + cycle_revenue - cycle_purchases - cycle_payouts, 2)


def get_weekly_cycle_data():
    with _connect() as conn:
        cash_in_hand = compute_cash_in_hand()
        weekly_start = float(conn.execute(
            "SELECT value FROM settings WHERE key = 'weekly_start_amount'"
        ).fetchone()['value'] or 400)
        now = datetime.now()
        days_since_thu = (now.weekday() - 3) % 7
        this_thursday = (now - timedelta(days=days_since_thu)).strftime('%Y-%m-%d')
        this_sunday = (datetime.strptime(this_thursday, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')
        thu_start = datetime.strptime(this_thursday, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
        sun_end = datetime.strptime(this_sunday, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        cycle_orders = _orders_in_range(conn, thu_start, sun_end)
        cycle_ids = [o['id'] for o in cycle_orders]
        cycle_revenue, cycle_cost = _revenue_and_cost(conn, cycle_ids)
        cycle_purchases = conn.execute(
            "SELECT COALESCE(SUM(price), 0) as total FROM purchase_items "
            "WHERE purchase_date >= ? AND purchase_date <= ?",
            (this_thursday, this_sunday),
        ).fetchone()['total']
        cycle_payouts = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
            "WHERE expense_date >= ? AND expense_date <= ?",
            (this_thursday, this_sunday),
        ).fetchone()['total']
        cycle_spent = cycle_purchases + cycle_payouts
        cycle_net = cycle_revenue - cycle_spent
        projected_end = weekly_start + cycle_net
        excess = max(0, projected_end - weekly_start)
        daily = []
        cursor = datetime.strptime(this_thursday, '%Y-%m-%d')
        end_dt = datetime.strptime(this_sunday, '%Y-%m-%d')
        while cursor <= end_dt:
            ds = cursor.strftime('%Y-%m-%d')
            day_ids = [o['id'] for o in _orders_in_range(
                conn,
                cursor.replace(hour=0, minute=0, second=0),
                cursor.replace(hour=23, minute=59, second=59),
            )]
            day_rev, day_cst = _revenue_and_cost(conn, day_ids)
            day_purch = conn.execute(
                "SELECT COALESCE(SUM(price), 0) as t FROM purchase_items WHERE purchase_date = ?", (ds,)
            ).fetchone()['t']
            day_exp = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as t FROM expenses WHERE expense_date = ?", (ds,)
            ).fetchone()['t']
            daily.append({
                'date': ds,
                'dayName': cursor.strftime('%A'),
                'orders': len(day_ids),
                'revenue': round(day_rev, 2),
                'cost': round(day_cst, 2),
                'purchases': round(day_purch, 2),
                'payouts': round(day_exp, 2),
                'spent': round(day_purch + day_exp, 2),
                'profit': round(day_rev - day_cst - day_exp, 2),
                'net': round(day_rev - day_purch - day_exp, 2),
            })
            cursor += timedelta(days=1)
    return {
        'cashInHand': round(cash_in_hand, 2),
        'weeklyStartAmount': round(weekly_start, 2),
        'cycleStart': this_thursday,
        'cycleEnd': this_sunday,
        'cycleRevenue': round(cycle_revenue, 2),
        'cycleCost': round(cycle_cost, 2),
        'cyclePurchases': round(cycle_purchases, 2),
        'cyclePayouts': round(cycle_payouts, 2),
        'cycleSpent': round(cycle_spent, 2),
        'cycleNet': round(cycle_net, 2),
        'projectedEnd': round(projected_end, 2),
        'excess': round(excess, 2),
        'daily': daily,
    }


def get_end_of_day_report(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    start = dt.replace(hour=0, minute=0, second=0)
    end = dt.replace(hour=23, minute=59, second=59)
    with _connect() as conn:
        orders = _orders_in_range(conn, start, end)
        ids = [o['id'] for o in orders]
        revenue, cost = _revenue_and_cost(conn, ids)
        items = []
        if ids:
            ph = ','.join('?' * len(ids))
            items = [dict(r) for r in conn.execute(
                f'SELECT mi.name, SUM(oi.quantity) as qty, '
                f'SUM(oi.price * oi.quantity) as revenue, '
                f'SUM(oi.cost * oi.quantity) as cost '
                f'FROM order_items oi JOIN menu_items mi ON oi.menu_item_id = mi.id '
                f'WHERE oi.order_id IN ({ph}) GROUP BY mi.id ORDER BY qty DESC',
                ids,
            ).fetchall()]
        day_purchases = conn.execute(
            "SELECT COALESCE(SUM(price), 0) as t FROM purchase_items WHERE purchase_date = ?",
            (date_str,),
        ).fetchone()['t']
        day_payouts = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as t FROM expenses WHERE expense_date = ?",
            (date_str,),
        ).fetchone()['t']
    profit = revenue - cost - day_payouts
    return {
        'date': date_str,
        'dayName': dt.strftime('%A'),
        'totalOrders': len(orders),
        'revenue': round(revenue, 2),
        'costOfGoods': round(cost, 2),
        'purchases': round(day_purchases, 2),
        'payouts': round(day_payouts, 2),
        'profit': round(profit, 2),
        'netCash': round(revenue - day_purchases - day_payouts, 2),
        'items': [{
            'name': i['name'],
            'qty': i['qty'],
            'revenue': round(i['revenue'], 2),
            'cost': round(i['cost'], 2),
            'profit': round(i['revenue'] - i['cost'], 2),
        } for i in items],
    }


def get_finance_summary():
    with _connect() as conn:
        rev_cog = conn.execute(
            'SELECT COALESCE(SUM(oi.price * oi.quantity), 0) as revenue, '
            'COALESCE(SUM(oi.cost * oi.quantity), 0) as cog '
            'FROM order_items oi JOIN orders o ON oi.order_id = o.id'
        ).fetchone()
        total_revenue = rev_cog['revenue']
        total_cog = rev_cog['cog']
        purch_row = conn.execute(
            'SELECT COALESCE(SUM(price), 0) as total, COUNT(*) as cnt FROM purchase_items'
        ).fetchone()
        total_purchases = purch_row['total']
        exp_row = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt FROM expenses'
        ).fetchone()
        total_expenses = exp_row['total']
        total_orders = conn.execute('SELECT COUNT(*) as cnt FROM orders').fetchone()['cnt']
        total_spent = total_purchases + total_expenses
        profit = total_revenue - total_cog - total_expenses
        transactions = []
        for t in conn.execute(
            'SELECT o.created_at as date, SUM(oi.price * oi.quantity) as amount '
            'FROM orders o JOIN order_items oi ON o.id = oi.order_id '
            'GROUP BY o.id ORDER BY o.created_at DESC LIMIT 20'
        ).fetchall():
            transactions.append({
                'type': 'income', 'label': 'Order revenue',
                'amount': round(t['amount'], 2),
                'date': (t['date'] or '')[:10],
            })
        for t in conn.execute(
            'SELECT pi.name, pi.price, pi.purchase_date, pi.created_at, pc.emoji '
            'FROM purchase_items pi JOIN purchase_categories pc ON pi.category_id = pc.id '
            'ORDER BY pi.created_at DESC LIMIT 20'
        ).fetchall():
            transactions.append({
                'type': 'purchase', 'label': f'{t["emoji"]} {t["name"]}',
                'amount': round(t['price'], 2),
                'date': t['purchase_date'] or (t['created_at'] or '')[:10],
            })
        for t in conn.execute(
            'SELECT description, amount, expense_date, created_at FROM expenses '
            'ORDER BY created_at DESC LIMIT 20'
        ).fetchall():
            transactions.append({
                'type': 'payout', 'label': t['description'],
                'amount': round(t['amount'], 2),
                'date': t['expense_date'] or (t['created_at'] or '')[:10],
            })
        transactions.sort(key=lambda x: x['date'], reverse=True)
        ws_row = conn.execute(
            "SELECT value FROM settings WHERE key = 'weekly_start_amount'"
        ).fetchone()
        weekly_start = float(ws_row['value']) if ws_row else 400.0
    live_cash = compute_cash_in_hand()
    return {
        'totalRevenue': round(total_revenue, 2),
        'totalPurchases': round(total_purchases, 2),
        'totalExpenses': round(total_expenses, 2),
        'totalSpent': round(total_spent, 2),
        'costOfGoods': round(total_cog, 2),
        'profit': round(profit, 2),
        'cashPosition': round(total_revenue - total_spent, 2),
        'cashInHand': round(live_cash, 2),
        'weeklyStartAmount': round(weekly_start, 2),
        'totalOrders': total_orders,
        'transactions': transactions[:30],
    }
