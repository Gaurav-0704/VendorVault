# Copyright (c) 2026 Gaurav Singh Thakur. MIT License.

import json
from flask import Blueprint, request, jsonify
from database import get_db, get_menu_items
from services.order_parser import parse_order_text

whatsapp_bp = Blueprint('whatsapp', __name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@whatsapp_bp.route('/api/whatsapp/config', methods=['GET'])
def get_config():
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
        'enabled': bool(config['enabled']),
    })


@whatsapp_bp.route('/api/whatsapp/config', methods=['PUT'])
def update_config():
    data = request.json
    db = get_db()
    existing = db.execute("SELECT * FROM whatsapp_config WHERE id = 1").fetchone()

    access_token = data.get('access_token', '')
    if access_token == '***' and existing:
        access_token = existing['access_token']

    if existing:
        db.execute(
            "UPDATE whatsapp_config SET phone_number_id=?, business_account_id=?, "
            "access_token=?, verify_token=?, enabled=? WHERE id=1",
            (data.get('phone_number_id', ''), data.get('business_account_id', ''),
             access_token, data.get('verify_token', ''), int(data.get('enabled', False))),
        )
    else:
        db.execute(
            "INSERT INTO whatsapp_config (id, phone_number_id, business_account_id, "
            "access_token, verify_token, enabled) VALUES (1,?,?,?,?,?)",
            (data.get('phone_number_id', ''), data.get('business_account_id', ''),
             access_token, data.get('verify_token', ''), int(data.get('enabled', False))),
        )

    db.commit()
    db.close()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Meta webhook handshake
# ---------------------------------------------------------------------------

@whatsapp_bp.route('/api/whatsapp/webhook', methods=['GET'])
def verify_webhook():
    db = get_db()
    config = db.execute("SELECT verify_token FROM whatsapp_config WHERE id=1").fetchone()
    db.close()

    mode = request.args.get('hub.mode', '')
    token = request.args.get('hub.verify_token', '')
    challenge = request.args.get('hub.challenge', '')

    if mode == 'subscribe' and config and token == config['verify_token']:
        return challenge, 200
    return 'Forbidden', 403


# ---------------------------------------------------------------------------
# Incoming message webhook
# ---------------------------------------------------------------------------

@whatsapp_bp.route('/api/whatsapp/webhook', methods=['POST'])
def receive_message():
    """Receive a WhatsApp message, parse it into a structured order, and store it."""
    data = request.json or {}
    db = get_db()

    try:
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        menu_names = [item['name'] for item in get_menu_items()]

        for msg in messages:
            sender = msg.get('from', '')
            text = msg.get('text', {}).get('body', '') or ''
            parsed = parse_order_text(text, menu_names=menu_names)
            db.execute(
                "INSERT INTO whatsapp_messages (sender, message, parsed_order, status) VALUES (?,?,?,?)",
                (sender, text, json.dumps(parsed.to_dict()), 'received'),
            )
    except (KeyError, IndexError, TypeError):
        pass

    db.commit()
    db.close()
    return jsonify({'status': 'ok'})


# ---------------------------------------------------------------------------
# Stand-alone parser endpoint (for testing / integrations)
# ---------------------------------------------------------------------------

@whatsapp_bp.route('/api/whatsapp/parse', methods=['POST'])
def parse_message():
    """Parse a free-text order message and return a structured order object.

    POST body: {"text": "2 veg noodles and 1 egg fried rice for Rahul"}
    Response:  {"customer": "Rahul", "lines": [...], "raw_text": "...", "unrecognized": []}
    """
    body = request.get_json(silent=True) or {}
    text = body.get('text', '')
    if not text:
        return jsonify({'error': 'text field is required'}), 400

    menu_names = [item['name'] for item in get_menu_items()]
    parsed = parse_order_text(text, menu_names=menu_names)
    return jsonify(parsed.to_dict())


# ---------------------------------------------------------------------------
# Message history
# ---------------------------------------------------------------------------

@whatsapp_bp.route('/api/whatsapp/messages', methods=['GET'])
def list_messages():
    db = get_db()
    rows = db.execute(
        "SELECT id, sender, message, parsed_order, status, created_at "
        "FROM whatsapp_messages ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    db.close()
    return jsonify([{
        'id': r['id'],
        'sender': r['sender'],
        'message': r['message'],
        'parsed_order': json.loads(r['parsed_order']) if r['parsed_order'] else None,
        'status': r['status'],
        'created_at': r['created_at'],
    } for r in rows])
