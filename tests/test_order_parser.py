"""Tests for the free-text order parser (services/order_parser.py).

Run with:  python -m pytest tests/
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.order_parser import parse_order_text, ParsedOrder, OrderLine

MENU = [
    "Veg Noodles",
    "Egg Noodles",
    "Chicken Noodles",
    "Double Egg Noodles",
    "Veg Fried Rice",
    "Egg Fried Rice",
    "Chicken Fried Rice",
    "Double Egg Fried Rice",
    "Chicken 65",
]


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------

def test_returns_parsed_order():
    result = parse_order_text("2 veg noodles", menu_names=MENU)
    assert isinstance(result, ParsedOrder)


def test_single_item_digit_quantity():
    result = parse_order_text("2 veg noodles", menu_names=MENU)
    assert len(result.lines) == 1
    assert result.lines[0].quantity == 2
    assert result.lines[0].item == "Veg Noodles"
    assert result.lines[0].confidence > 0.5


def test_multiple_items_comma_separated():
    result = parse_order_text("2 veg noodles, 1 chicken 65", menu_names=MENU)
    assert len(result.lines) == 2
    items = {l.item for l in result.lines}
    assert "Veg Noodles" in items
    assert "Chicken 65" in items


def test_multiple_items_and_separator():
    result = parse_order_text("3 egg fried rice and 2 chicken noodles", menu_names=MENU)
    assert len(result.lines) == 2


def test_word_quantity():
    result = parse_order_text("two veg noodles", menu_names=MENU)
    assert result.lines[0].quantity == 2


def test_quantity_with_x_suffix():
    result = parse_order_text("3x chicken 65", menu_names=MENU)
    assert result.lines[0].quantity == 3
    assert result.lines[0].item == "Chicken 65"


# ---------------------------------------------------------------------------
# Customer name extraction
# ---------------------------------------------------------------------------

def test_customer_from_for_pattern():
    result = parse_order_text("2 veg noodles for Rahul", menu_names=MENU)
    assert result.customer == "Rahul"


def test_customer_from_from_pattern():
    result = parse_order_text("order from Priya: 1 egg fried rice", menu_names=MENU)
    assert result.customer == "Priya"


def test_customer_in_parentheses():
    result = parse_order_text("2 chicken 65 (Amit)", menu_names=MENU)
    assert result.customer == "Amit"


def test_no_customer_when_absent():
    result = parse_order_text("1 veg noodles", menu_names=MENU)
    assert result.customer is None


# ---------------------------------------------------------------------------
# Messy / informal inputs
# ---------------------------------------------------------------------------

def test_noise_words_stripped():
    result = parse_order_text("please send 2 veg noodles", menu_names=MENU)
    assert len(result.lines) == 1
    assert result.lines[0].item == "Veg Noodles"


def test_typo_tolerance():
    # "veg noddles" should still match "Veg Noodles"
    result = parse_order_text("2 veg noddles", menu_names=MENU)
    assert len(result.lines) == 1
    assert result.lines[0].item == "Veg Noodles"


def test_typo_chicken():
    result = parse_order_text("3 chiken 65", menu_names=MENU)
    assert len(result.lines) == 1
    assert result.lines[0].item == "Chicken 65"


def test_informal_abbreviation():
    result = parse_order_text("2 veg noodles n 1 egg rice", menu_names=MENU)
    # At least veg noodles parsed
    item_names = [l.item for l in result.lines]
    assert "Veg Noodles" in item_names


def test_hi_greeting_ignored():
    result = parse_order_text("hi can i get 2 veg noodles", menu_names=MENU)
    assert len(result.lines) == 1
    assert result.lines[0].item == "Veg Noodles"


def test_full_messy_order():
    text = "plz send 3 chiken 65 n 2 veg noddles from Rahul"
    result = parse_order_text(text, menu_names=MENU)
    assert result.customer == "Rahul"
    item_names = [l.item for l in result.lines]
    assert "Chicken 65" in item_names
    assert "Veg Noodles" in item_names


# ---------------------------------------------------------------------------
# No-menu fallback
# ---------------------------------------------------------------------------

def test_no_menu_returns_raw_fragments():
    result = parse_order_text("2 veg noodles and 1 egg rice", menu_names=None)
    assert len(result.lines) >= 1
    assert result.lines[0].quantity == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_string():
    result = parse_order_text("")
    assert result.lines == []
    assert result.customer is None


def test_whitespace_only():
    result = parse_order_text("   ")
    assert result.lines == []


def test_to_dict_shape():
    result = parse_order_text("2 veg noodles for Rahul", menu_names=MENU)
    d = result.to_dict()
    assert "customer" in d
    assert "lines" in d
    assert "raw_text" in d
    assert "unrecognized" in d
    assert d["lines"][0]["item"] == "Veg Noodles"
    assert d["lines"][0]["quantity"] == 2
    assert "confidence" in d["lines"][0]


def test_unrecognized_populated_for_bad_input():
    result = parse_order_text("2 unicorn soup", menu_names=MENU)
    assert len(result.unrecognized) == 1
    assert result.lines == []
