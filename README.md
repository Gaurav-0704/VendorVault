# VendorVault

I built VendorVault for the way a real cloud kitchen actually runs: orders coming in over WhatsApp, cash moving in and out through the day, and a constant question at the back of my mind — *am I actually making money on this?*

Most restaurant software answers "how much did I sell?". VendorVault answers "how much did I sell, what did it cost me, and how much cash should be in the drawer right now?" It's designed around real-time cloud kitchen operations — WhatsApp-first ordering, purchase-driven costing, and a weekly cash cycle.

It runs on a laptop, opens on a phone over WiFi during service, and now deploys to the cloud with owner login and optional AI insights.

---

## What Makes VendorVault Different

This is the part that matters. On the surface it looks like any other restaurant dashboard. It isn't.

### 1. WhatsApp-Native Order Processing
Every other system expects orders through a POS terminal or a dedicated app. My customers text me on WhatsApp in mixed language with typos — *"bhai 2 veg noddles n 1 chiken 65 for Rahul"*. VendorVault reads that message and turns it into a structured order: customer name, items, quantities — automatically.

```
Input:  "plz send 3 chiken 65 n 2 veg noddles from Rahul"
Output: customer = Rahul, items = [Chicken 65 ×3, Veg Noodles ×2]
```

It handles typos, informal separators ("n", "and", "+"), word quantities ("two", "three"), and greeting noise ("hi", "please", "bhai") — all with Python's standard library, no external ML service.

### 2. Purchase-First Costing
Most systems track sales and guess at cost. VendorVault tracks every vendor purchase — chicken, eggs, oil, packaging — with real quantities and prices. So when it shows a menu item's profit, that number is grounded in what I actually paid, not an estimate.

### 3. Live Cash-in-Hand
One number tells me exactly how much cash should be in the drawer at any moment:

```
Cash = Starting Balance + Order Revenue − Purchases − Payouts
```

Every order adds to it, every purchase and payout subtracts. If the physical count drifts, I correct it in one tap and the system rebalances.

### 4. Weekly Cash Cycle
A cloud kitchen's week isn't Monday–Sunday. Mine runs Thursday to Sunday. On Monday I count the drawer, pull the excess over my float, and bank it. VendorVault models this cycle day by day — running total, expected pullout, next week's starting float.

### 5. Inventory That Updates Itself
Stock goes up when I log a purchase, down when an order is placed. No separate inventory screen to maintain — it falls out of what I've bought and sold.

### 6. Optional AI, On Your Own Key
Add your own Anthropic API key and VendorVault turns on a weekly business digest, smart reorder alerts, and auto-written WhatsApp order confirmations. No key? Everything else works exactly the same. You're never paying for AI you didn't ask for.

---

## Features

| Module | What it does |
|--------|--------------|
| **Dashboard** | Today / week / month revenue, profit margin, recent orders |
| **Orders** | Tap-to-order menu grid, mobile-friendly, supports backdating |
| **WhatsApp** | Parses free-text messages into structured orders |
| **Purchases** | Log vendor purchases by category, with a bulk-entry mode |
| **Finance** | Live cash-in-hand, weekly cycle, end-of-day report |
| **Stock** | Auto-updated inventory levels per category |
| **Payouts** | Staff wages and expenses, deducted from cash |
| **Reports** | Daily / weekly / monthly revenue, cost, profit |
| **Profits** | Margin per menu item, revenue vs cost |
| **Cost Analysis** | Spend grouped by purchase category |
| **AI Insights** | Weekly digest, reorder alerts (needs your API key) |
| **Settings** | Business info, currency, API key, account |

---

## Architecture

```
Frontend     Single-page React (index.html) — no build step, no node_modules
Backend      Flask, Python 3.9+, one blueprint per feature
Database     SQLite with WAL mode and foreign keys
Auth         Signed-session owner login (werkzeug), env-based credentials
AI           Anthropic SDK — Haiku for real-time, Sonnet for analysis (optional)
Parser       Pure stdlib (re + difflib), no external NLP service
Deploy       Docker + gunicorn, Railway-ready, persistent volume for the DB
Tests        pytest (parser) + scripted API/auth/AI smoke tests
```

**Project layout:**
```
app.py                  Entry point — routes, auth guard, blueprint registration
start.py                Production start script (seed then gunicorn)
database.py             Compatibility shim — re-exports from db/
db/                     Database logic split by concern
routes/
  whatsapp.py             WhatsApp webhook + parse endpoints
  ai.py                   AI feature endpoints (gated on API key)
services/
  order_parser.py         Free-text → ParsedOrder dataclass
  ai.py                   Claude-powered digest / reorder / confirmation
tests/
  test_order_parser.py    21 parser tests
index.html              Full React frontend
Dockerfile              Container build for Railway / Docker
railway.toml            Railway deploy config (health check, restart policy)
```

---

## Installation

**Requirements:** Python 3.9+ and pip. Nothing else for local use.

```bash
git clone https://github.com/Gaurav-0704/VendorVault.git
cd VendorVault

pip install -r requirements.txt
python seed.py        # run once — creates and seeds the database
python app.py         # starts the server on http://localhost:5000
```

Default login is `owner` / `vendorvault` — change it with env vars before deploying anywhere public.

To reach it from your phone on the same WiFi, open **Settings → Network Access** in the app for the exact URL.

### Environment Variables

Copy `.env.example` to `.env`. Everything has a sensible default for local use.

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `5000` | Server port |
| `DEBUG` | `false` | Dev mode (auto-reload, detailed errors) |
| `DB_DIR` | project root | Where the SQLite file lives — point at a mounted volume in the cloud |
| `APP_USERNAME` | `owner` | Owner login username |
| `APP_PASSWORD` | `vendorvault` | Owner login password — **change this** |
| `APP_SECRET_KEY` | dev default | Signs the session cookie — set a long random string in production |
| `WHATSAPP_VERIFY_TOKEN` | — | Meta webhook verification |
| `WHATSAPP_ACCESS_TOKEN` | — | Meta API access |
| `AI_MODEL_FAST` | `claude-haiku-4-5-20251001` | Model for real-time AI (reorder, confirmations) |
| `AI_MODEL_SMART` | `claude-sonnet-5` | Model for analysis (weekly digest) |

The Anthropic API key isn't an env var — the owner adds it in **Settings → AI API Key**, so it's stored per-install and never committed.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

```
21 passed
```

The parser suite covers clean input, typos (`noddles`→Noodles, `chiken`→Chicken), mixed separators, word quantities, customer-name extraction, greeting noise, and edge cases like empty strings.

---

## Evaluation

Verified behavior, not just claims. Each area below was smoke-tested against a running server.

### Core app — all endpoints healthy
A fresh, empty database directory serves all 15 GET endpoints plus the parser with HTTP 200 — the app self-heals its schema on startup, so a clean cloud container never fails its health check.

### Parser accuracy
| Input | Result |
|-------|--------|
| `2 veg noddles` | Veg Noodles ×2 ✓ |
| `3 chiken 65` | Chicken 65 ×3 ✓ |
| `two egg fried rice` | Egg Fried Rice ×2 ✓ |
| `2 veg noodles n 1 egg rice` | 2 items ✓ |
| `plz send 3 chiken 65 n 2 veg noddles from Rahul` | customer = Rahul, 2 items ✓ |
| `2 unicorn soup` | unrecognized (not a false match) ✓ |

### Authentication
| Check | Result |
|-------|--------|
| `/health` reachable when logged out | 200 ✓ |
| `/api/*` blocked when logged out | 401 ✓ |
| Wrong password rejected | 401 ✓ |
| Login → access → logout → blocked again | ✓ |

### AI layer (optional)
| Check | Result |
|-------|--------|
| Status reports disabled with no key | ✓ |
| Feature endpoints return a clean "add your key" response, no crash | ✓ |
| Key set → status flips to enabled | ✓ |
| API key never exposed in `/api/settings` (masked) | ✓ |
| Key delete → AI switches off, rest of app unaffected | ✓ |

### Known limitations
- **SQLite** is single-writer — perfect for one kitchen on one instance. A multi-location or multi-staff rollout would move to PostgreSQL; the data layer is isolated in `db/` for exactly that migration.
- **WhatsApp webhook** needs a public URL (a cloud deploy, or ngrok for local testing).
- **Auth** is a single owner account by design — not multi-user RBAC.

---

## Deployment

VendorVault ships with a `Dockerfile` and `railway.toml`. The container seeds the database, then runs gunicorn. Point `DB_DIR` at a mounted volume so data survives redeploys, set `APP_PASSWORD` / `APP_SECRET_KEY`, and the health check at `/health` confirms the app is live.

---

## License

MIT — Copyright (c) 2026 Gaurav Singh Thakur. See [LICENSE](LICENSE).
