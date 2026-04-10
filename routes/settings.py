# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — Settings Routes

from flask import Blueprint, request, jsonify
from database import get_db

bp = Blueprint('settings', __name__)


@bp.route('/api/settings')
def get_settings():
    db   = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return jsonify({r['key']: r['value'] for r in rows})


@bp.route('/api/settings', methods=['POST'])
def update_settings():
    db   = get_db()
    data = request.json
    for key, value in data.items():
        db.execute(
            "INSERT OR REPLACE INTO settings "
            "(key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, str(value)),
        )
    db.commit()
    return jsonify({'success': True})
