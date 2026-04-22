# Binance Futures Testnet Trading Bot

A clean, structured Python CLI application for placing orders on the **Binance Futures Testnet (USDT-M)**. Built for the Primetrade.ai Python Developer internship assignment.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package metadata
│   ├── client.py            # Binance REST API client (signing, requests, errors)
│   ├── orders.py            # Order placement logic (MARKET, LIMIT, STOP)
│   ├── validators.py        # Input validation helpers
│   ├── logging_config.py    # Structured rotating-file + console logging
│   └── cli.py               # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── .env.example             # Copy to .env and add your keys
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / unzip the project

```bash
cd trading_bot
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API credentials

1. Register at [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Go to **API Management** → generate a key pair
3. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
```

---

## How to Run

All commands are run from the project root (`trading_bot/`):

```bash
python -m bot.cli <command> [options]
```

### Place a MARKET order

```bash
# Buy 0.01 BTC at market price
python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --qty 0.01

# Sell 0.05 ETH at market price
python -m bot.cli place --symbol ETHUSDT --side SELL --type MARKET --qty 0.05
```

### Place a LIMIT order

```bash
# Sell 0.01 BTC at $67,000 (GTC)
python -m bot.cli place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.01 --price 67000

# Buy 0.1 ETH at $3,000 (IOC)
python -m bot.cli place --symbol ETHUSDT --side BUY --type LIMIT --qty 0.1 --price 3000 --tif IOC
```

### Place a STOP / STOP_MARKET order *(bonus)*

```bash
# Stop-limit buy ETH: trigger at $3,050, fill at $3,100
python -m bot.cli place --symbol ETHUSDT --side BUY --type STOP \
    --qty 0.1 --price 3100 --stop-price 3050

# Stop-market sell BTC: trigger at $60,000
python -m bot.cli place --symbol BTCUSDT --side SELL --type STOP_MARKET \
    --qty 0.01 --stop-price 60000
```

### View account balances

```bash
python -m bot.cli account
```

### List open orders

```bash
python -m bot.cli open-orders
python -m bot.cli open-orders --symbol BTCUSDT
```

---

## Sample Output

```
──── ORDER REQUEST ────────────────────────────────────
Symbol      : BTCUSDT
Side        : BUY
Order Type  : MARKET
Quantity    : 0.01

──── ORDER RESPONSE ───────────────────────────────────
Order ID    : 3917421
Symbol      : BTCUSDT
Status      : FILLED
Side        : BUY
Type        : MARKET
Orig Qty    : 0.01
Executed Qty: 0.01
Avg Price   : 64823.10
────────────────────────────────────────────────────────
✔  Order placed successfully!
```

---

## Logging

- All API requests, responses, and errors are written to `logs/trading_bot.log`.
- Rotating log: max 5 MB per file, 3 backups kept.
- Format: `TIMESTAMP | LEVEL | LOGGER | MESSAGE`
- Signatures are **redacted** in log output for security.

Sample log entries are included in `logs/trading_bot.log`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API keys | Clear message + exit 1 |
| Invalid symbol / side / type | `ValidationError` with hint |
| Missing price on LIMIT order | `ValidationError` |
| Binance API error (e.g. -2019) | Shows code + message |
| Network / timeout failure | Descriptive error + exit 1 |

---

## Assumptions

- Targets **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`).
- `timeInForce` defaults to `GTC` for LIMIT/STOP orders; override with `--tif`.
- No position-side hedge mode (one-way mode assumed).
- Quantity precision is passed as-is; the testnet may reject values that exceed instrument precision — check `exchangeInfo` if needed.

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP REST calls to Binance API |
| `python-dotenv` | Load `.env` credentials |

No third-party Binance SDK is used — all API calls are raw REST with HMAC-SHA256 signing.
