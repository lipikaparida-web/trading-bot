"""Binance Futures Testnet REST API client wrapper."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://demo-fapi.binance.com"
RECV_WINDOW = 5000  # ms


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.
    Handles HMAC-SHA256 signing, request logging, and error mapping.
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceClient initialised. Base URL: %s", self.base_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> str:
        """Return HMAC-SHA256 signature for the given query string."""
        query = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _signed_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append timestamp, recvWindow, and signature to params."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        params["signature"] = self._sign(params)
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Any:
        """Generic HTTP request with logging and error handling."""
        params = params or {}
        if signed:
            params = self._signed_params(params)

        url = f"{self.base_url}{path}"
        logger.info("REQUEST  %s %s | params=%s", method.upper(), path, self._safe_params(params))

        try:
            response = self._session.request(
                method, url, params=params if method.upper() == "GET" else None,
                data=params if method.upper() == "POST" else None,
                timeout=10,
            )
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error: %s", exc)
            raise ConnectionError(f"Could not connect to Binance testnet: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise TimeoutError("Request to Binance testnet timed out.") from exc

        logger.info(
            "RESPONSE %s %s | status=%s body=%s",
            method.upper(),
            path,
            response.status_code,
            response.text[:500],
        )

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text)
            response.raise_for_status()
            return {}

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        return data

    @staticmethod
    def _safe_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Return params with signature redacted for logging."""
        safe = dict(params)
        if "signature" in safe:
            safe["signature"] = "***"
        return safe

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_exchange_info(self) -> Any:
        """Fetch exchange / symbol information (unsigned)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account(self) -> Any:
        """Fetch futures account information."""
        return self._request("GET", "/fapi/v2/account")

    def new_order(self, **kwargs: Any) -> Any:
        """Place a new futures order."""
        return self._request("POST", "/fapi/v1/order", params=dict(kwargs))

    def cancel_order(self, symbol: str, order_id: int) -> Any:
        """Cancel an existing order."""
        return self._request(
            "DELETE", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id}
        )

    def get_order(self, symbol: str, order_id: int) -> Any:
        """Query a single order by ID."""
        return self._request("GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id})

    def get_open_orders(self, symbol: Optional[str] = None) -> Any:
        """Fetch all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)
