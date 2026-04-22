"""Order placement logic for Binance Futures Testnet."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .client import BinanceClient
from .logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderRequest:
    """Represents a validated order before submission."""

    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"

    def summary(self) -> str:
        parts = [
            f"Symbol      : {self.symbol}",
            f"Side        : {self.side}",
            f"Order Type  : {self.order_type}",
            f"Quantity    : {self.quantity}",
        ]
        if self.price is not None:
            parts.append(f"Price       : {self.price}")
        if self.stop_price is not None:
            parts.append(f"Stop Price  : {self.stop_price}")
        if self.order_type in {"LIMIT", "STOP"}:
            parts.append(f"Time in Force: {self.time_in_force}")
        return "\n".join(parts)


@dataclass
class OrderResult:
    """Parsed response from a submitted order."""

    order_id: int
    symbol: str
    status: str
    side: str
    order_type: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    raw: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Order ID    : {self.order_id}\n"
            f"Symbol      : {self.symbol}\n"
            f"Status      : {self.status}\n"
            f"Side        : {self.side}\n"
            f"Type        : {self.order_type}\n"
            f"Orig Qty    : {self.orig_qty}\n"
            f"Executed Qty: {self.executed_qty}\n"
            f"Avg Price   : {self.avg_price}"
        )


def _parse_order_result(data: Dict[str, Any]) -> OrderResult:
    return OrderResult(
        order_id=data.get("orderId", -1),
        symbol=data.get("symbol", ""),
        status=data.get("status", ""),
        side=data.get("side", ""),
        order_type=data.get("type", ""),
        orig_qty=data.get("origQty", "0"),
        executed_qty=data.get("executedQty", "0"),
        avg_price=data.get("avgPrice", data.get("price", "0")),
        raw=data,
    )


def place_market_order(client: BinanceClient, req: OrderRequest) -> OrderResult:
    """Submit a MARKET order."""
    logger.info(
        "Placing MARKET order: symbol=%s side=%s qty=%s",
        req.symbol, req.side, req.quantity,
    )
    params: Dict[str, Any] = {
        "symbol": req.symbol,
        "side": req.side,
        "type": "MARKET",
        "quantity": req.quantity,
    }
    data = client.new_order(**params)
    result = _parse_order_result(data)
    logger.info("MARKET order placed: orderId=%s status=%s", result.order_id, result.status)
    return result


def place_limit_order(client: BinanceClient, req: OrderRequest) -> OrderResult:
    """Submit a LIMIT order."""
    logger.info(
        "Placing LIMIT order: symbol=%s side=%s qty=%s price=%s",
        req.symbol, req.side, req.quantity, req.price,
    )
    params: Dict[str, Any] = {
        "symbol": req.symbol,
        "side": req.side,
        "type": "LIMIT",
        "quantity": req.quantity,
        "price": req.price,
        "timeInForce": req.time_in_force,
    }
    data = client.new_order(**params)
    result = _parse_order_result(data)
    logger.info("LIMIT order placed: orderId=%s status=%s", result.order_id, result.status)
    return result


def place_stop_order(client: BinanceClient, req: OrderRequest) -> OrderResult:
    """Submit a STOP_MARKET or STOP (stop-limit) order."""
    if req.price is not None:
        order_type = "STOP"
        logger.info(
            "Placing STOP order: symbol=%s side=%s qty=%s price=%s stopPrice=%s",
            req.symbol, req.side, req.quantity, req.price, req.stop_price,
        )
        params: Dict[str, Any] = {
            "symbol": req.symbol,
            "side": req.side,
            "type": "STOP",
            "quantity": req.quantity,
            "price": req.price,
            "stopPrice": req.stop_price,
            "timeInForce": req.time_in_force,
        }
    else:
        order_type = "STOP_MARKET"
        logger.info(
            "Placing STOP_MARKET order: symbol=%s side=%s qty=%s stopPrice=%s",
            req.symbol, req.side, req.quantity, req.stop_price,
        )
        params = {
            "symbol": req.symbol,
            "side": req.side,
            "type": "STOP_MARKET",
            "quantity": req.quantity,
            "stopPrice": req.stop_price,
        }

    data = client.new_order(**params)
    result = _parse_order_result(data)
    logger.info("%s order placed: orderId=%s status=%s", order_type, result.order_id, result.status)
    return result


def dispatch_order(client: BinanceClient, req: OrderRequest) -> OrderResult:
    """Route order to the correct placement function based on type."""
    if req.order_type == "MARKET":
        return place_market_order(client, req)
    elif req.order_type == "LIMIT":
        return place_limit_order(client, req)
    elif req.order_type in {"STOP", "STOP_MARKET"}:
        return place_stop_order(client, req)
    else:
        raise ValueError(f"Unsupported order type: {req.order_type}")
