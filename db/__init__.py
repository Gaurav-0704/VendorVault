# Gaurav Singh Thakur — MIT License
from db.connection import get_db, DB_PATH
from db.schema import init_db
from db.settings import get_all_settings, set_setting
from db.menu import (
    add_menu_category, get_menu_categories, delete_menu_category,
    add_menu_item, get_menu_items, get_menu_item, delete_menu_item,
    update_menu_item, get_menu_with_categories,
)
from db.orders import create_order, get_orders, delete_order
from db.purchases import (
    add_purchase_category, get_purchase_categories, delete_purchase_category,
    add_purchase_item, add_purchase_items_bulk, get_purchase_items,
    delete_purchase_item, get_purchases_with_categories,
    update_stock, get_stock_levels,
)
from db.expenses import add_expense, get_expenses, delete_expense
from db.reports import (
    get_daily_report, get_weekly_report, get_monthly_report,
    get_profits_data, get_cost_analysis,
)
from db.finance import (
    update_cash_in_hand, compute_cash_in_hand,
    get_weekly_cycle_data, get_end_of_day_report, get_finance_summary,
)
from db.dashboard import get_dashboard_stats
