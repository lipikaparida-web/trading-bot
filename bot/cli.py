#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
  Market buy:
    python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --qty 0.01

  Limit sell:
    python -m bot.cli place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.01 --price 70000

  Stop-limit buy:
    python -m bot.cli place --symbol ETHUSDT --side BUY --type STOP --qty 0.1 \
        --price 3100 --stop-price 3050

  Account info:
    python -m bot.cli account
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from .client import BinanceAPIError, BinanceClient
from .logging_config import setup_logging
from .orders import OrderRequest, dispatch_order
from .validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

# ── Colour helpers ──────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"{GREEN}{BOLD}✔  {msg}{RESET}")


def _err(msg: str) -> None:
    print(f"{RED}{BOLD}✘  {msg}{RESET}", file=sys.stderr)


def _info(label: str, value: str) -> None:
    print(f"  {CYAN}{label:<14}{RESET} {value}")


def _sep(title: str = "") -> None:
    line = "─" * 52
    if title:
        print(f"\n{YELLOW}{BOLD}{'─'*4} {title} {'─'*(46 - len(title))}{RESET}")
    else:
        print(f"{YELLOW}{line}{RESET}")


# ── Client factory ──────────────────────────────────────────────────────────

def _build_client() -> BinanceClient:
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        _err(
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set as environment variables "
            "or in a .env file."
        )
        sys.exit(1)
    return BinanceClient(api_key, api_secret)


# ── Sub-command handlers ────────────────────────────────────────────────────

def cmd_place(args: argparse.Namespace) -> None:
    """Validate inputs, build order request, dispatch to Binance."""
    logger = setup_logging()  # ensure logging is active

    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        order_type = validate_order_type(args.type)
        quantity = validate_quantity(args.qty)
        price = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValidationError as exc:
        _err(str(exc))
        sys.exit(1)

    req = OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=args.tif.upper(),
    )

    _sep("ORDER REQUEST")
    print(req.summary())

    client = _build_client()

    try:
        result = dispatch_order(client, req)
    except ValidationError as exc:
        _err(f"Validation: {exc}")
        sys.exit(1)
    except BinanceAPIError as exc:
        _err(f"API error [{exc.code}]: {exc.message}")
        sys.exit(1)
    except (ConnectionError, TimeoutError) as exc:
        _err(f"Network: {exc}")
        sys.exit(1)

    _sep("ORDER RESPONSE")
    print(result.summary())
    _sep()
    _ok("Order placed successfully!")


def cmd_account(args: argparse.Namespace) -> None:
    """Fetch and display account information."""
    setup_logging()
    client = _build_client()
    try:
        data = client.get_account()
    except BinanceAPIError as exc:
        _err(f"API error [{exc.code}]: {exc.message}")
        sys.exit(1)
    except (ConnectionError, TimeoutError) as exc:
        _err(f"Network: {exc}")
        sys.exit(1)

    _sep("ACCOUNT INFO")
    _info("Total Wallet:", data.get("totalWalletBalance", "N/A"))
    _info("Available:", data.get("availableBalance", "N/A"))
    _info("Total PnL:", data.get("totalUnrealizedProfit", "N/A"))
    _info("Can Trade:", str(data.get("canTrade", "N/A")))

    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    if assets:
        _sep("ASSETS WITH BALANCE")
        for asset in assets:
            _info(asset["asset"], asset["walletBalance"])
    _sep()


def cmd_open_orders(args: argparse.Namespace) -> None:
    """List open orders."""
    setup_logging()
    client = _build_client()
    try:
        orders = client.get_open_orders(symbol=args.symbol or None)
    except BinanceAPIError as exc:
        _err(f"API error [{exc.code}]: {exc.message}")
        sys.exit(1)

    if not orders:
        print("No open orders.")
        return

    _sep("OPEN ORDERS")
    for o in orders:
        print(
            f"  {o.get('orderId')} | {o.get('symbol')} | {o.get('side')} | "
            f"{o.get('type')} | qty={o.get('origQty')} | price={o.get('price')} | "
            f"status={o.get('status')}"
        )
    _sep()


# ── Argument parser ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── place ──
    place_p = sub.add_parser("place", help="Place a new futures order")
    place_p.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    place_p.add_argument("--side", required=True, help="BUY or SELL")
    place_p.add_argument("--type", required=True, dest="type", help="MARKET | LIMIT | STOP | STOP_MARKET")
    place_p.add_argument("--qty", required=True, help="Order quantity")
    place_p.add_argument("--price", default=None, help="Limit price (required for LIMIT/STOP)")
    place_p.add_argument("--stop-price", default=None, dest="stop_price", help="Stop trigger price (STOP/STOP_MARKET)")
    place_p.add_argument("--tif", default="GTC", help="Time-in-force: GTC | IOC | FOK (default: GTC)")
    place_p.set_defaults(func=cmd_place)

    # ── account ──
    acct_p = sub.add_parser("account", help="Show account balances")
    acct_p.set_defaults(func=cmd_account)

    # ── open-orders ──
    oo_p = sub.add_parser("open-orders", help="List open orders")
    oo_p.add_argument("--symbol", default=None, help="Filter by symbol (optional)")
    oo_p.set_defaults(func=cmd_open_orders)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
