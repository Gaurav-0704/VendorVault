# Gaurav Singh Thakur — MIT License
#
# Note: the running app (app.py) handles /api/settings inline. This blueprint
# is kept for the modular layout but isn't the active settings handler.

from flask import Blueprint, request, jsonify
from database import get_db

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/settings', methods=['GET'])
def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    db.close()
    return jsonify({r['key']: r['value'] for r in rows})


@settings_bp.route('/api/settings', methods=['PUT'])
def update_settings():
    """I upsert each key individually so I can send partial updates without wiping everything."""
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
