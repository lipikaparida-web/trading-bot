"""Input validation for trading bot CLI arguments."""

from __future__ import annotations

import re
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP"}

# Binance symbol pattern: uppercase letters only, 2-20 chars
SYMBOL_RE = re.compile(r"^[A-Z]{2,20}$")


class ValidationError(ValueError):
    """Raised when user input fails validation."""


def validate_symbol(symbol: str) -> str:
    """Normalise and validate a trading pair symbol (e.g. BTCUSDT)."""
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Must be uppercase letters only, e.g. BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    """Validate order side (BUY / SELL)."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str) -> float:
    """Parse and validate order quantity."""
    try:
        qty = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {qty}.")
    return qty


def validate_price(price: Optional[str], order_type: str) -> Optional[float]:
    """
    Validate price field.
    - Required for LIMIT and STOP orders.
    - Ignored for MARKET orders.
    """
    if order_type in {"LIMIT", "STOP"}:
        if price is None:
            raise ValidationError(f"Price is required for {order_type} orders.")
        try:
            p = float(price)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid price '{price}'. Must be a positive number.")
        if p <= 0:
            raise ValidationError(f"Price must be greater than 0, got {p}.")
        return p
    # MARKET / STOP_MARKET — price ignored
    return None


def validate_stop_price(stop_price: Optional[str], order_type: str) -> Optional[float]:
    """Validate stop price — required for STOP / STOP_MARKET orders."""
    if order_type in {"STOP", "STOP_MARKET"}:
        if stop_price is None:
            raise ValidationError(f"Stop price is required for {order_type} orders.")
        try:
            sp = float(stop_price)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid stop price '{stop_price}'. Must be a positive number.")
        if sp <= 0:
            raise ValidationError(f"Stop price must be greater than 0, got {sp}.")
        return sp
    return None
