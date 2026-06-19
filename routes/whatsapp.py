# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.

import re
from flask import Blueprint, request, jsonify
from database import get_db

whatsapp_bp = Blueprint('whatsapp', __name__)


@whatsapp_bp.route('/api/whatsapp/config', methods=['GET'])
def get_config():
    """Get WhatsApp integration configuration."""
    db = get_db()
    config = db.execute("SELECT * FROM whatsapp_config WHERE id = 1").fetchone()
    db.close()
    if not config:
        return jsonify({'enabled': False})
    return jsonify({
        'phone_number_id': config['phone_number_id'] or '',
        'business_account_id': config['business_account_id'] or '',
        'access_token': '***' if config['access_token'] else '',
        'verify_token': config['verify_token'] or '',
        'enabled': bool(config['enabled'])
    })


@whatsapp_bp.route('/api/whatsapp/config', methods=['PUT'])
def update_config():
    """Update WhatsApp configuration."""
    data = request.json
    db = get_db()
    existing = db.execute("SELECT * FROM whatsapp_config WHERE id = 1").fetchone()

    access_token = data.get('access_token', '')
    if access_token == '***' and existing:
        access_token = existing['access_token']

    if existing:
        db.execute("""
            UPDATE whatsapp_config SET phone_number_id = ?, business_account_id = ?,
                   access_token = ?, verify_token = ?, enabled = ? WHERE id = 1
        """, (data.get('phone_number_id', ''), data.get('business_account_id', ''),
              access_token, data.get('verify_token', ''), int(data.get('enabled', False))))
    else:
        db.execute("""
            INSERT INTO whatsapp_config (id, phone_number_id, business_account_id, access_token, verify_token, enabled)
            VALUES (1, ?, ?, ?, ?, ?)
        """, (data.get('phone_number_id', ''), data.get('business_account_id', ''),
              access_token, data.get('verify_token', ''), int(data.get('enabled', False))))

    db.commit()
    db.close()
    return jsonify({'success': True})


@whatsapp_bp.route('/api/whatsapp/webhook', methods=['GET'])
def verify_webhook():
    """Meta webhook verification endpoint."""
    db = get_db()
    config = db.execute("SELECT verify_token FROM whatsapp_config WHERE id = 1").fetchone()
    db.close()

    mode = request.args.get('hub.mode', '')
    token = request.args.get('hub.verify_token', '')
    challenge = request.args.get('hub.challenge', '')

    if mode == 'subscribe' and config and token == config['verify_token']:
        return challenge, 200
    return 'Forbidden', 403


@whatsapp_bp.route('/api/whatsapp/webhook', methods=['POST'])
def receive_message():
    """Receive and parse incoming WhatsApp messages."""
    data = request.json
    db = get_db()

    try:
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        for msg in messages:
            sender = msg.get('from', '')
            text = msg.get('text', {}).get('body', '')
            parsed = _parse_order_text(text)

            db.execute(
                "INSERT INTO whatsapp_messages (sender, message, parsed_order, status) VALUES (?, ?, ?, ?)",
                (sender, text, str(parsed), 'received')
            )
    except (KeyError, IndexError):
        pass

    db.commit()
    db.close()
    return jsonify({'status': 'ok'})


@whatsapp_bp.route('/api/whatsapp/messages', methods=['GET'])
def list_messages():
    """List recent WhatsApp messages."""
    db = get_db()
    messages = db.execute(
        "SELECT * FROM whatsapp_messages ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    db.close()
    return jsonify([{
        'id': m['id'], 'sender': m['sender'], 'message': m['message'],
        'parsed_order': m['parsed_order'], 'status': m['status'],
        'created_at': m['created_at']
    } for m in messages])


def _parse_order_text(text):
    """Simple regex-based order parser for common patterns."""
    items = []
    patterns = [
        r'(\d+)\s*x?\s*(veg\s*noodles?|egg\s*noodles?|chicken\s*noodles?|double\s*egg\s*noodles?)',
        r'(\d+)\s*x?\s*(veg\s*fried\s*rice|egg\s*fried\s*rice|chicken\s*fried\s*rice|double\s*egg\s*fried\s*rice)',
        r'(\d+)\s*x?\s*(chicken\s*65)',
    ]
    for pattern in patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            items.append({'qty': int(match.group(1)), 'item': match.group(2).strip().title()})
    return items
