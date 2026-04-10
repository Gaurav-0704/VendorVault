# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — App Factory

from flask import Flask
from config import SECRET_KEY
from database import close_db
from routes import register_all


def create_app():
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
    )
    app.config['SECRET_KEY'] = SECRET_KEY

    app.teardown_appcontext(close_db)
    register_all(app)

    return app


# Allow "python app.py" as an alternative entry point
if __name__ == '__main__':
    from config import DEBUG, HOST, PORT
    from database import init_db, seed_default_data

    init_db()
    seed_default_data()

    app = create_app()
    print("\n  🚀 VendorVault running at http://localhost:5000\n")
    app.run(debug=DEBUG, host=HOST, port=PORT)
