# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Route Registration

from routes.dashboard  import bp as dashboard_bp
from routes.menu       import bp as menu_bp
from routes.orders     import bp as orders_bp
from routes.purchases  import bp as purchases_bp
from routes.reports    import bp as reports_bp
from routes.expenses   import bp as expenses_bp
from routes.whatsapp   import bp as whatsapp_bp
from routes.settings   import bp as settings_bp


def register_all(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(settings_bp)
