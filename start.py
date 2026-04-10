#!/usr/bin/env python3
# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Quick Start

import subprocess
import sys
import os


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        import flask  # noqa: F401
    except ImportError:
        print("  📦 Installing Flask …")
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', 'flask']
        )

    os.makedirs('data', exist_ok=True)

    print("""
    ╔══════════════════════════════════════════════╗
    ║         ⚡  VendorVault  v1.0                ║
    ║         Smart Sales & Profit Tracker         ║
    ╠══════════════════════════════════════════════╣
    ║  Open → http://localhost:5000                ║
    ║  Stop → Ctrl + C                             ║
    ╚══════════════════════════════════════════════╝
    """)

    from database import init_db, seed_default_data
    from app import create_app
    from config import DEBUG, HOST, PORT

    init_db()
    seed_default_data()

    app = create_app()
    app.run(debug=DEBUG, host=HOST, port=PORT)


if __name__ == '__main__':
    main()
