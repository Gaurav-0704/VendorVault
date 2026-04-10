# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.
# VendorVault — WhatsApp Integration Routes

import re
import json
from flask import Blueprint, request, jsonify
from database import get_db

bp = Blueprint('whatsapp', __name__)


# ── Config ───────────────────────────────────────────────────────────────────

@bp.route('/api/whatsapp/config')
def get_config():
    db     = get_db()
    config = db.execute(
        "SELECT * FROM whatsapp_config WHERE id = 1"
    ).fetchone()
    return jsonify(dict(config) if config else {})


@bp.route('/api/whatsapp/config', methods=['POST'])
def update_config():
    db   = get_db()
    data = request.json
    db.execute('''
        INSERT OR REPLACE INTO whatsapp_config
            (id, phone_number, api_token, webhook_secret,
             is_enabled, auto_confirm)
        VALUES (1, ?, ?, ?, ?, ?)
    ''', (
        data.get('phone_number', ''),
        data.get('api_token', ''),
        data.get('webhook_secret', ''),
        data.get('is_enabled', 0),
        data.get('auto_confirm', 0),
    ))
    db.commit()
    return jsonify({'success': True})


# ── Webhook ──────────────────────────────────────────────────────────────────

@bp.route('/api/whatsapp/webhook', methods=['GET'])
def webhook_verify():
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    db     = get_db()
    config = db.execute(
        "SELECT webhook_secret FROM whatsapp_config WHERE id=1"
    ).fetchone()
    secret = config['webhook_secret'] if config else ''

    if mode == 'subscribe' and token == secret:
        return challenge, 200
    return 'Forbidden', 403


@bp.route('/api/whatsapp/webhook', methods=['POST'])
def webhook_receive():
    data = request.json
    db   = get_db()

    try:
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                messages = change.get('value', {}).get('messages', [])
                for msg in messages:
                    from_number = msg.get('from', '')
                    text        = msg.get('text', {}).get('body', '')

                    db.execute('''
                        INSERT INTO whatsapp_messages
                            (message_id, from_number, message_text)
                        VALUES (?, ?, ?)
                    ''', (msg.get('id', ''), from_number, text))

                    parsed = _parse_order(text, db)
                    if parsed:
                        db.execute('''
                            UPDATE whatsapp_messages
                            SET parsed_order = ?, is_processed = 1
                            WHERE message_id = ?
                        ''', (json.dumps(parsed), msg.get('id', '')))

        db.commit()
    except Exception as e:
        print(f"WhatsApp webhook error: {e}")

    return jsonify({'status': 'ok'})


# ── Message Log ──────────────────────────────────────────────────────────────

@bp.route('/api/whatsapp/messages')
def get_messages():
    db   = get_db()
    rows = db.execute(
        "SELECT * FROM whatsapp_messages ORDER BY received_at DESC LIMIT 50"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Simple Order Parser ─────────────────────────────────────────────────────

def _parse_order(text, db):
    text_lower  = text.lower()
    menu_items  = db.execute(
        "SELECT id, name FROM menu_items WHERE is_available = 1"
    ).fetchall()

    found = []
    for item in menu_items:
        name_lower = item['name'].lower()
        if name_lower in text_lower:
            qty = 1
            for pattern in [
                rf'(\d+)\s*(?:x\s*)?{re.escape(name_lower)}',
                rf'{re.escape(name_lower)}\s*(?:x\s*)?(\d+)',
            ]:
                match = re.search(pattern, text_lower)
                if match:
                    qty = int(match.group(1))
                    break
            found.append({
                'menu_item_id': item['id'],
                'name':         item['name'],
                'quantity':     qty,
            })

    return found if found else None
