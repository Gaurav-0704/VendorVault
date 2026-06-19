# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.

from flask import Blueprint, request, jsonify
from database import get_db

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/settings', methods=['GET'])
def get_settings():
    """Get all application settings."""
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    db.close()
    return jsonify({r['key']: r['value'] for r in rows})


@settings_bp.route('/api/settings', methods=['PUT'])
def update_settings():
    """Update application settings (key-value pairs)."""
    data = request.json
    db = get_db()
    for key, value in data.items():
        existing = db.execute("SELECT key FROM settings WHERE key = ?", (key,)).fetchone()
        if existing:
            db.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))
        else:
            db.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    db.commit()
    db.close()
    return jsonify({'success': True})
