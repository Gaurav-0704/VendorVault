# Gaurav Singh Thakur — MIT License
#
# HTTP endpoints for the optional AI features. Each one degrades gracefully:
# if there's no API key, it returns a clean 'add your key' response instead of
# crashing, and the frontend shows a friendly prompt.

from flask import Blueprint, request, jsonify

from services import ai
from database import (
    get_weekly_report, get_stock_levels, get_dashboard_stats,
    get_cost_analysis,
)

ai_bp = Blueprint('ai', __name__)


def _no_key_response():
    return jsonify({
        'enabled': False,
        'error': 'no_api_key',
        'message': 'Add your Anthropic API key in Settings to turn on AI features.',
    }), 400


def _ai_error(e):
    # Real failures (bad key, network, model issue) — surface a short message
    return jsonify({'enabled': True, 'error': 'ai_failed', 'message': str(e)}), 502


@ai_bp.route('/api/ai/status')
def ai_status():
    """Cheap check the frontend uses to decide whether to show AI panels."""
    return jsonify({'enabled': ai.is_enabled()})


def _as_list(value, key='categories'):
    """get_cost_analysis and friends sometimes return a dict, sometimes a list.
    Normalize to a list so downstream code never slices a dict."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        inner = value.get(key)
        return inner if isinstance(inner, list) else []
    return []


@ai_bp.route('/api/ai/digest')
def ai_digest():
    # Check the key up front so the no-key path is deterministic and cheap
    if not ai.is_enabled():
        return _no_key_response()
    try:
        weekly = get_weekly_report()
        dash = get_dashboard_stats() or {}
        top = dash.get('top_items') or dash.get('top_sellers') or []
        cost_list = _as_list(get_cost_analysis())
        text = ai.weekly_digest(weekly, top_items=top, cost_by_category=cost_list)
        return jsonify({'enabled': True, 'digest': text})
    except ai.AIKeyMissing:
        return _no_key_response()
    except Exception as e:
        return _ai_error(e)


@ai_bp.route('/api/ai/reorder')
def ai_reorder():
    if not ai.is_enabled():
        return _no_key_response()
    try:
        stock = get_stock_levels()
        text = ai.reorder_suggestions(stock)
        return jsonify({'enabled': True, 'suggestions': text})
    except ai.AIKeyMissing:
        return _no_key_response()
    except Exception as e:
        return _ai_error(e)


@ai_bp.route('/api/ai/confirm', methods=['POST'])
def ai_confirm():
    if not ai.is_enabled():
        return _no_key_response()
    try:
        parsed = request.get_json(silent=True) or {}
        text = ai.confirmation_message(parsed)
        return jsonify({'enabled': True, 'message': text})
    except ai.AIKeyMissing:
        return _no_key_response()
    except Exception as e:
        return _ai_error(e)
