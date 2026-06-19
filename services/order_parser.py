# Gaurav Singh Thakur — MIT License
#
# This is the parser I wrote to handle WhatsApp order messages. Customers text in
# things like "2 veg noddles n 1 chiken 65 for Rahul" and I need to turn that into
# a clean structured object I can actually work with.
#
# I deliberately kept this dependency-free (just stdlib re and difflib) so it
# runs anywhere without any pip install. The fuzzy matching handles typos well
# enough for a small fixed menu.
#
# Usage:
#   from services.order_parser import parse_order_text
#   result = parse_order_text("2 veg noodles for Rahul", menu_names=["Veg Noodles", ...])
#   result.to_dict()

import re
import difflib
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class OrderLine:
    item: str           # matched menu item name (or raw fragment if no menu given)
    quantity: int
    confidence: float   # 1.0 = exact match, lower = fuzzy


@dataclass
class ParsedOrder:
    customer: Optional[str]
    lines: list          # list[OrderLine]
    raw_text: str
    unrecognized: list   # fragments that looked like items but didn't match anything

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

# Patterns I use to find the customer name in a message
_CUSTOMER_PATTERNS = [
    r"\bfor\s+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
    r"\bfrom\s+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
    r"\(([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\)",
    r"^([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\s*[:\-,]",
    r"\bcustomer[:\s]+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
    r"\bname[:\s]+([A-Za-z][a-z]+(?: [A-Za-z][a-z]+)?)\b",
]

# Words I strip out before trying to match item names
_NOISE = re.compile(
    r"\b(please|plz|pls|send|get|need|want|give|order|hi|hello|"
    r"can i|i want|i need|could you|kindly|just|also|plus|with|add)\b",
    re.IGNORECASE,
)

# Matches digit quantities like "2", "3x", or word quantities like "two"
_QTY_RE = re.compile(
    r"(\d+)\s*x?|(" + "|".join(_WORD_TO_INT) + r")\b",
    re.IGNORECASE,
)


def _extract_customer(text: str) -> tuple[Optional[str], str]:
    """Tries each customer pattern in order and returns the first name it finds,
    along with the text with that phrase removed."""
    for pat in _CUSTOMER_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip().title()
            # don't accidentally treat a food word as a name
            if name.lower() in {"noodles", "rice", "chicken", "egg", "veg"}:
                continue
            cleaned = text[:m.start()] + text[m.end():]
            return name, cleaned.strip()
    return None, text


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _best_match(fragment: str, menu_names: list[str], cutoff: float = 0.55) -> tuple[Optional[str], float]:
    """Fuzzy-matches a raw item fragment against my menu. Returns (matched_name, confidence)."""
    if not menu_names:
        return None, 0.0

    norm_fragment = _normalize(fragment)
    norm_menu = [_normalize(n) for n in menu_names]

    # exact substring → full confidence
    for i, nm in enumerate(norm_menu):
        if norm_fragment in nm or nm in norm_fragment:
            return menu_names[i], 1.0

    # fall back to difflib sequence matching
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
    """Parses a free-text order message into a structured ParsedOrder.

    I split on common delimiters first (comma, 'and', 'n', '+'), then strip
    noise words from each chunk, then pull out the quantity and match the
    remaining fragment against the menu using fuzzy matching.

    Args:
        text:       Raw message, e.g. "plz send 2 veg noddles n 1 chiken 65 for Rahul"
        menu_names: My current menu item names for fuzzy matching.
                    If None, I return the raw fragment as the item name.

    Returns:
        ParsedOrder with customer, lines, raw_text, and unrecognized fragments.
    """
    if not text or not text.strip():
        return ParsedOrder(customer=None, lines=[], raw_text=text or "", unrecognized=[])

    customer, working = _extract_customer(text.strip())
    working = re.sub(r"\s+", " ", working).strip()

    lines: list[OrderLine] = []
    unrecognized: list[str] = []

    # Split on delimiters BEFORE stripping noise so "and"/"n" work as separators
    chunks = re.split(r"[,;/\n]|\band\b|\bn\b|\+|&", working, flags=re.IGNORECASE)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        # strip noise words from this chunk
        chunk = _NOISE.sub(" ", chunk)
        chunk = re.sub(r"\s+", " ", chunk).strip()
        if not chunk:
            continue

        qty_match = _QTY_RE.match(chunk.strip())
        if qty_match:
            qty = int(qty_match.group(1)) if qty_match.group(1) else _WORD_TO_INT[qty_match.group(2).lower()]
            item_fragment = chunk[qty_match.end():].strip()
        else:
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
                unrecognized.append(item_fragment)
        else:
            lines.append(OrderLine(item=item_fragment.title(), quantity=qty, confidence=0.5))

    return ParsedOrder(
        customer=customer,
        lines=lines,
        raw_text=text,
        unrecognized=unrecognized,
    )
