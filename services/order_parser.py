# Copyright (c) 2026 Gaurav Singh Thakur. MIT License.
"""
Free-text order parser: natural-language-in / structured-data-out.

Accepts a raw WhatsApp message and returns a ParsedOrder with typed fields
(customer name, line items with quantities and fuzzy-matched menu names).
No external dependencies — uses stdlib re and difflib only.

Usage:
    from services.order_parser import parse_order_text, ParsedOrder
    result = parse_order_text("2 veg noodles and 1 egg fried rice for Rahul", menu_names=["Veg Noodles", ...])
    result.to_dict()  # → {"customer": "Rahul", "lines": [...], ...}
"""

import re
import difflib
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class OrderLine:
    item: str           # matched (or raw) item name
    quantity: int
    confidence: float   # 0.0–1.0; 1.0 = exact match, <1.0 = fuzzy


@dataclass
class ParsedOrder:
    customer: Optional[str]
    lines: list          # list[OrderLine]
    raw_text: str
    unrecognized: list   # fragments that looked like items but didn't match

    def to_dict(self) -> dict:
        return {
            "customer": self.customer,
            "lines": [
                {"item": l.item, "quantity": l.quantity, "confidence": round(l.confidence, 2)}
                for l in self.lines
            ],
            "raw_text": self.raw_text,
            "unrecognized": self.unrecognized,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_WORD_TO_INT = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}

# Patterns that introduce a customer name; capture group 1 = the name.
_CUSTOMER_PATTERNS = [
    r"\bfor\s+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
    r"\bfrom\s+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
    r"\(([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\)",
    r"^([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\s*[:\-,]",
    r"\bcustomer[:\s]+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
    r"\bname[:\s]+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
]

# Noise words to strip per-chunk after splitting (do NOT include "and"/"n" here
# because they are used as delimiters before noise stripping).
_NOISE = re.compile(
    r"\b(please|plz|pls|send|get|need|want|give|order|hi|hello|"
    r"can i|i want|i need|could you|kindly|just|also|plus|with|add)\b",
    re.IGNORECASE,
)

# Quantity token: digit(s) optionally followed by 'x', or a word-number.
_QTY_RE = re.compile(
    r"(\d+)\s*x?|(" + "|".join(_WORD_TO_INT) + r")\b",
    re.IGNORECASE,
)


def _extract_customer(text: str) -> tuple[Optional[str], str]:
    """Return (customer_name_or_None, text_with_customer_phrase_removed)."""
    for pat in _CUSTOMER_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip().title()
            # Don't mistake menu words for names
            if name.lower() in {"noodles", "rice", "chicken", "egg", "veg"}:
                continue
            cleaned = text[:m.start()] + text[m.end():]
            return name, cleaned.strip()
    return None, text


def _normalize(s: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for comparison."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _best_match(fragment: str, menu_names: list[str], cutoff: float = 0.55) -> tuple[Optional[str], float]:
    """Fuzzy-match a raw fragment against menu item names using difflib."""
    if not menu_names:
        return None, 0.0

    norm_fragment = _normalize(fragment)
    norm_menu = [_normalize(n) for n in menu_names]

    # Try exact substring first (highest confidence)
    for i, nm in enumerate(norm_menu):
        if norm_fragment in nm or nm in norm_fragment:
            return menu_names[i], 1.0

    # Fall back to sequence matcher
    matches = difflib.get_close_matches(norm_fragment, norm_menu, n=1, cutoff=cutoff)
    if matches:
        idx = norm_menu.index(matches[0])
        score = difflib.SequenceMatcher(None, norm_fragment, matches[0]).ratio()
        return menu_names[idx], score

    return None, 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_order_text(text: str, menu_names: Optional[list] = None) -> ParsedOrder:
    """Parse a free-text order message into a structured ParsedOrder.

    Args:
        text: Raw message, e.g. "2 veg noodles n 1 egg fried rice for Rahul"
        menu_names: Known menu item names for fuzzy matching.
                    If None/empty, raw extracted fragments are used as item names.

    Returns:
        ParsedOrder with customer, lines (OrderLine list), raw_text, unrecognized.
    """
    if not text or not text.strip():
        return ParsedOrder(customer=None, lines=[], raw_text=text or "", unrecognized=[])

    customer, working = _extract_customer(text.strip())
    working = re.sub(r"\s+", " ", working).strip()

    lines: list[OrderLine] = []
    unrecognized: list[str] = []

    # Split on common delimiters BEFORE stripping noise so "and"/"n" act as separators.
    chunks = re.split(r"[,;/\n]|\band\b|\bn\b|\+|&", working, flags=re.IGNORECASE)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        # Strip noise words from this chunk before parsing
        chunk = _NOISE.sub(" ", chunk)
        chunk = re.sub(r"\s+", " ", chunk).strip()
        if not chunk:
            continue

        # Find quantity at the start of the chunk
        qty_match = _QTY_RE.match(chunk.strip())
        if qty_match:
            if qty_match.group(1):  # digit
                qty = int(qty_match.group(1))
            else:                   # word number
                qty = _WORD_TO_INT[qty_match.group(2).lower()]
            item_fragment = chunk[qty_match.end():].strip()
        else:
            # No leading quantity — default to 1, treat whole chunk as item
            qty = 1
            item_fragment = chunk

        item_fragment = item_fragment.strip(" .,!?-")
        if not item_fragment:
            continue

        if menu_names:
            matched, confidence = _best_match(item_fragment, menu_names)
            if matched:
                lines.append(OrderLine(item=matched, quantity=qty, confidence=confidence))
            else:
                # Store with low confidence using the raw fragment
                unrecognized.append(item_fragment)
        else:
            # No menu provided — accept raw fragment as-is
            lines.append(OrderLine(
                item=item_fragment.title(),
                quantity=qty,
                confidence=0.5,
            ))

    return ParsedOrder(
        customer=customer,
        lines=lines,
        raw_text=text,
        unrecognized=unrecognized,
    )
