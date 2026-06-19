# Gaurav Singh Thakur — MIT License
#
# Collects all blueprints so app.py can register them with one call.

from routes.dashboard import dashboard_bp
from routes.orders import orders_bp
from routes.menu import menu_bp
from routes.purchases import purchases_bp
from routes.reports import reports_bp
from routes.expenses import expenses_bp
from routes.whatsapp import whatsapp_bp
from routes.settings import settings_bp
from routes.pwa import pwa_bp


def register_all(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(pwa_bp)
