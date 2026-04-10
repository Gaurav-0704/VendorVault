# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Config

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE = os.path.join(BASE_DIR, 'data', 'vendorvault.db')

# ── Flask ────────────────────────────────────────────────────────────────────
SECRET_KEY = 'vendorvault-change-me-in-production'
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000
