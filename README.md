# VendorVault

I built VendorVault for the way a real cloud kitchen actually runs: orders coming in over WhatsApp, cash moving in and out through the day, and one question always at the back of my mind — *am I actually making money on this?*

Most restaurant software tells you how much you sold. VendorVault tells you how much you sold, what it cost, and how much cash should be in the drawer right now. It runs on a laptop, opens on a phone over WiFi during service, and deploys to the cloud with a private owner login.

## Try It

Live demo: **[vendorvault.up.railway.app](https://vendorvault.up.railway.app)**

Sign in with `owner` / `vendorvault` to look around.

---

## What Makes It Different

### WhatsApp-Native Orders
Customers text their orders in plain language, typos and all — *"bhai 2 veg noddles n 1 chiken 65 for Rahul"*. VendorVault reads the message and turns it into a clean order with the customer, items, and quantities.

```
Input:  "plz send 3 chiken 65 n 2 veg noddles from Rahul"
Output: customer = Rahul, items = [Chicken 65 ×3, Veg Noodles ×2]
```

It handles typos, informal separators ("n", "and", "+"), word quantities ("two", "three"), and greeting noise ("hi", "please", "bhai").

### Purchase-First Costing
Every vendor purchase — chicken, eggs, oil, packaging — is logged with real quantities and prices. So a menu item's profit is based on what you actually paid, not an estimate.

### Live Cash-in-Hand
One number shows exactly how much cash should be in the drawer at any moment:

```
Cash = Starting Balance + Order Revenue − Purchases − Payouts
```

Orders add to it, purchases and payouts subtract. If the physical count drifts, you correct it in one tap and the system rebalances.

### Weekly Cash Cycle
A cloud kitchen's week isn't Monday–Sunday. Mine runs Thursday to Sunday. On Monday you count the drawer, pull the excess over your float, and bank it. VendorVault tracks the cycle day by day — running total, expected pullout, next week's starting float.

### Inventory That Updates Itself
Stock rises when you log a purchase and falls when an order is placed. There's no separate inventory screen to maintain — it follows from what you've bought and sold.

### Optional AI Insights
Add your own Anthropic API key to turn on a weekly business digest, smart reorder alerts, and auto-written WhatsApp order confirmations. Without a key, everything else works exactly the same.

---

## The Interface

VendorVault is a single, fast dashboard — dark theme, sidebar navigation on desktop, a tap-friendly layout on mobile. Each section is one focused screen.

| Screen | What you do there |
|--------|-------------------|
| **Dashboard** | See today / week / month revenue, profit margin, and recent orders at a glance |
| **Orders** | Tap items off the menu grid to place an order; supports backdating |
| **WhatsApp** | Free-text messages parsed into structured orders |
| **Purchases** | Log vendor purchases by category, with a bulk-entry mode for restock days |
| **Finance** | Live cash-in-hand, the weekly cycle, and an end-of-day report |
| **Stock** | Current inventory levels per category, updated automatically |
| **Payouts** | Staff wages and expenses, deducted from cash |
| **Reports** | Daily, weekly, and monthly revenue, cost, and profit |
| **Profits** | Margin per menu item and revenue against cost |
| **Cost Analysis** | Spend grouped by purchase category |
| **AI Insights** | Weekly digest and reorder suggestions |
| **Settings** | Business details, currency, API key, and account |

Every screen works the same on a phone — the sidebar collapses to a menu, cards stack into a single column, and buttons stay large enough to tap during service.

---

## Architecture

```
Frontend     Single-page React (index.html) — no build step, no node_modules
Backend      Flask, Python 3.9+, one blueprint per feature
Database     SQLite with WAL mode and foreign keys
Auth         Signed-session owner login, credentials from env
Parser       Python standard library (re + difflib)
AI           Anthropic SDK — Haiku for real-time, Sonnet for analysis (optional)
Deploy       Docker, Railway-ready
```

```
app.py                  Entry point — routes, auth, blueprint registration
start.py                Seeds the database, then starts the server
db/                     Database logic, split by concern
routes/                 One blueprint per feature (whatsapp, ai, …)
services/
  order_parser.py         Free-text → structured order
  ai.py                   Digest, reorder, and confirmation helpers
tests/                  Parser test suite
index.html              The full frontend
Dockerfile              Container build
railway.toml            Railway deploy config
```

---

## Installation

**Requirements:** Python 3.9+ and pip.

```bash
git clone https://github.com/Gaurav-0704/VendorVault.git
cd VendorVault

pip install -r requirements.txt
python seed.py        # run once — creates and seeds the database
python app.py         # http://localhost:5000
```

Default login is `owner` / `vendorvault`. Change it with env vars before deploying anywhere public. To open it on your phone over the same WiFi, use **Settings → Network Access** for the exact URL.

### Environment Variables

Copy `.env.example` to `.env`. Everything has a sensible default for local use.

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `5000` | Server port |
| `DEBUG` | `false` | Dev mode |
| `DB_DIR` | project root | Where the database file lives — point at a mounted volume in the cloud |
| `APP_USERNAME` | `owner` | Login username |
| `APP_PASSWORD` | `vendorvault` | Login password — change this |
| `APP_SECRET_KEY` | dev default | Signs the session cookie — set a random string in production |
| `WHATSAPP_VERIFY_TOKEN` | — | Meta webhook verification |
| `WHATSAPP_ACCESS_TOKEN` | — | Meta API access |
| `AI_MODEL_FAST` | `claude-haiku-4-5-20251001` | Model for real-time AI |
| `AI_MODEL_SMART` | `claude-sonnet-5` | Model for analysis |

The Anthropic API key isn't an env var — you add it in **Settings → AI API Key**, so it stays per-install and is never committed.

---

## Tests

```bash
python -m pytest tests/
```

The parser suite covers clean input, typos (`noddles`→Noodles, `chiken`→Chicken), mixed separators, word quantities, customer-name extraction, greeting noise, and edge cases. A full end-to-end check lives in `scripts/smoke_test.py`.

---

## Deployment

VendorVault ships with a `Dockerfile` and `railway.toml`. On Railway, connect the GitHub repo and it builds and runs on its own. Set `APP_PASSWORD` and `APP_SECRET_KEY`, and mount a volume at `/app/data` with `DB_DIR=/app/data` so data survives redeploys. The health check at `/health` confirms the app is live.

---

## License

MIT — Copyright (c) 2026 Gaurav Singh Thakur. See [LICENSE](LICENSE).
