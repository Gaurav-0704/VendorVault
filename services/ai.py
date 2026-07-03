# Gaurav Singh Thakur — MIT License
#
# The AI layer. Everything here is optional — it only runs if the owner has
# added their own Anthropic API key in Settings. No key, no calls, no cost.
# The rest of VendorVault works exactly the same whether this is on or off.
#
# I keep the Anthropic import inside the functions so the app starts fine even
# if the anthropic package isn't installed (e.g. a minimal local checkout).

import os

from db.connection import get_db

# Models are overridable via env so I can tune cost/quality without a code change.
# Fast model for quick, cheap, real-time replies. Smart model for analysis.
FAST_MODEL = os.environ.get('AI_MODEL_FAST', 'claude-haiku-4-5-20251001')
SMART_MODEL = os.environ.get('AI_MODEL_SMART', 'claude-sonnet-5')


class AIKeyMissing(Exception):
    """Raised when an AI feature is called but no API key is configured."""
    pass


def get_api_key():
    """Reads the owner's Anthropic key from settings. Returns None if unset."""
    db = get_db()
    try:
        row = db.execute("SELECT value FROM settings WHERE key = 'ai_api_key'").fetchone()
    finally:
        db.close()
    if row and row['value']:
        return row['value']
    return None


def is_enabled():
    return get_api_key() is not None


def _run(model, system, prompt, max_tokens=700):
    """Single place that actually talks to Claude. Raises AIKeyMissing if no key."""
    key = get_api_key()
    if not key:
        raise AIKeyMissing()
    # Imported lazily so a missing package never breaks app startup
    from anthropic import Anthropic
    client = Anthropic(api_key=key)
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return ''.join(block.text for block in msg.content if getattr(block, 'type', '') == 'text').strip()


# ---------------------------------------------------------------------------
# Feature 1 — Weekly business digest (uses the smart model)
# ---------------------------------------------------------------------------

def weekly_digest(weekly_report, top_items=None, cost_by_category=None):
    """Turns this week's raw numbers into a short, plain-English summary an owner
    would actually read over morning chai."""
    lines = [
        f"Revenue this week: {weekly_report.get('revenue', 0)}",
        f"Cost this week: {weekly_report.get('expenses', 0)}",
        f"Profit this week: {weekly_report.get('profit', 0)}",
        f"Orders this week: {weekly_report.get('orders', 0)}",
    ]
    if top_items:
        lines.append("Top sellers: " + ", ".join(
            f"{i.get('name', '?')} ({i.get('qty', i.get('total_qty', 0))})" for i in top_items[:5]
        ))
    if cost_by_category:
        lines.append("Spend by category: " + ", ".join(
            f"{c.get('category', c.get('name', '?'))}={c.get('total', c.get('amount', 0))}"
            for c in cost_by_category[:8]
        ))
    system = (
        "You are a sharp, practical restaurant business advisor. "
        "Keep it under 120 words. Be specific and direct — no fluff, no buzzwords. "
        "Point out one thing going well and one thing to watch. Talk like a helpful friend, not a consultant."
    )
    prompt = "Here are this week's numbers for my restaurant:\n" + "\n".join(lines) + \
             "\n\nGive me a short summary and one concrete suggestion."
    return _run(SMART_MODEL, system, prompt, max_tokens=400)


# ---------------------------------------------------------------------------
# Feature 2 — Smart reorder alerts (uses the fast model)
# ---------------------------------------------------------------------------

def reorder_suggestions(stock_levels, recent_usage=None):
    """Looks at current stock and recent movement and flags what to reorder."""
    lines = ["Current stock levels:"]
    for s in stock_levels:
        lines.append(f"  {s.get('item_name') or s.get('category') or '?'}: "
                     f"{s.get('quantity', 0)} {s.get('unit', '')}")
    if recent_usage:
        lines.append("\nRecent usage (last few days):")
        for u in recent_usage:
            lines.append(f"  {u.get('name', '?')}: {u.get('qty', 0)}")
    system = (
        "You are an inventory assistant for a small restaurant. "
        "Look at the stock and flag only the items that genuinely need reordering soon. "
        "Be concise — a short bulleted list. If nothing needs reordering, say so plainly. "
        "No preamble, no buzzwords."
    )
    prompt = "\n".join(lines) + "\n\nWhat should I reorder, and roughly how much?"
    return _run(FAST_MODEL, system, prompt, max_tokens=400)


# ---------------------------------------------------------------------------
# Feature 3 — WhatsApp order confirmation (uses the fast model)
# ---------------------------------------------------------------------------

def confirmation_message(parsed_order, currency='₹'):
    """Writes a friendly WhatsApp reply confirming a parsed order."""
    customer = parsed_order.get('customer') or 'there'
    items = parsed_order.get('lines', [])
    item_text = ", ".join(f"{i['quantity']}x {i['item']}" for i in items) or "your order"
    system = (
        "You write short, warm WhatsApp confirmation messages for a restaurant. "
        "One or two lines, friendly, include the items and ask them to confirm. "
        "Match the casual tone customers use. No emojis overload — one at most."
    )
    prompt = (f"Customer name: {customer}\nItems: {item_text}\n"
              f"Write a WhatsApp reply confirming this order and asking them to reply 'yes' to confirm.")
    return _run(FAST_MODEL, system, prompt, max_tokens=150)
