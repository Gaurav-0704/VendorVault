# VendorVault

I built VendorVault because I was running a restaurant and had no real picture of where my money went. I knew my revenue. I didn't know my actual profit. I couldn't answer "how much did I spend on chicken this week?" without digging through paper receipts. And when customers ordered on WhatsApp, I was copying messages into a notebook by hand.

So I built this — a restaurant management system that runs on my laptop, opens on my phone over WiFi during service, and gives me the numbers I actually care about in real time.

---

## What VendorVault Does

| Module | What it handles |
|--------|----------------|
| **Dashboard** | Today's revenue, weekly/monthly totals, hourly chart, top sellers, recent orders |
| **Orders** | Menu grid → tap items → place order. Works on mobile. Supports backdating. |
| **WhatsApp** | Parses free-text WhatsApp messages into structured orders automatically |
| **Purchases** | Log every vendor purchase by category with quantity, unit, and price |
| **Finance** | Live cash-in-hand, weekly cycle tracker, end-of-day breakdown |
| **Stock** | Inventory levels updated automatically from purchases and orders |
| **Payouts** | Staff wages and miscellaneous expenses, deducted from cash-in-hand |
| **Reports** | Daily, weekly, monthly — revenue, cost, profit, per-item breakdown |
| **Profits** | Margin per menu item, revenue vs cost, what's worth keeping on the menu |
| **Cost Analysis** | Spending by purchase category, week over week |
| **Settings** | Business name, currency, starting cash balance |

---

## What Makes VendorVault Different

Most restaurant systems are built around taking orders and printing receipts. VendorVault is built around understanding the full financial picture of running a restaurant.

### WhatsApp-Native Order Processing
Every other system expects orders through a POS terminal or a dedicated app. My customers text me on WhatsApp in mixed language with typos — *"bhai 2 veg noddles n 1 chiken 65 for Rahul"*. VendorVault parses that message directly into a structured order with the customer name, items, and quantities extracted automatically.

The parser handles typos, informal separators, word quantities ("two", "three"), and greeting noise ("hi", "please") — all using Python's standard library with no external ML dependencies.

```
Input:  "plz send 3 chiken 65 n 2 veg noddles from Rahul"
Output: customer=Rahul, items=[Chicken 65 ×3, Veg Noodles ×2]
```

### Purchase-First Financial Tracking
Most systems focus on sales. VendorVault tracks what I actually spend. Every vendor purchase is logged with quantity and price, so my profit numbers are based on real cost of goods — not estimates.

### Live Cash-in-Hand
The Finance screen shows exactly how much cash should be in my drawer at any moment:

```
Cash = Starting Balance + Order Revenue − Purchases − Payouts
```

If the drawer count drifts, I correct it in one tap and the system adjusts the baseline automatically.

### Weekly Cycle Management
My service week runs Thursday to Sunday. On Monday I count the drawer, pull the excess, and bank it. VendorVault models this cycle day by day — showing the running total, expected pullout, and the float going into next week.

### Inventory Without Manual Entry
Stock levels update automatically — up when I log a purchase, down when an order is placed. I don't manage inventory separately. It falls out of what I've bought and sold.

### No Dependencies, No Setup Complexity
No Node.js. No Docker required. No database server. One command installs everything, one command starts it. The entire frontend is a single HTML file with no build step.

---

## Architecture

```
Frontend     Single-page React app (index.html) — no build step, no node_modules
Backend      Flask, Python 3.9+, one blueprint per feature
Database     SQLite with WAL mode and foreign keys
Parser       Pure stdlib (re + difflib) — no external NLP libraries
Tests        pytest — 21 tests covering the WhatsApp order parser
```

**Project structure:**
```
app.py                  Entry point — registers all blueprints
database.py             Compatibility shim — re-exports from db/
db/                     Database logic split by concern
  connection.py           SQLite setup and context manager
  schema.py               Table definitions, created on first run
  menu.py                 Menu categories and items
  orders.py               Order creation and retrieval
  purchases.py            Purchase logging and stock levels
  expenses.py             Payouts and expenses
  reports.py              Daily, weekly, monthly report queries
  finance.py              Cash-in-hand, weekly cycle, end-of-day
  dashboard.py            Aggregated dashboard stats
  settings.py             Key-value settings store
routes/                 One Flask blueprint per feature
services/
  order_parser.py         Free-text → ParsedOrder dataclass
tests/
  test_order_parser.py    21 parser tests
index.html              Full React frontend
seed.py                 Initial menu and purchase categories
requirements.txt        Flask + gunicorn
```

---

## Installation

**Requirements:** Python 3.9+, pip. Nothing else.

```bash
git clone https://github.com/Gaurav-0704/VendorVault.git
cd VendorVault

pip install -r requirements.txt
python seed.py        # run once — sets up the database with starting data
python app.py         # starts the server
```

Open `http://localhost:5000` in your browser.

To access from your phone on the same WiFi network, go to **Settings → Network Access** inside the app — it shows the exact URL to open on your phone.

**Environment variables** (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Port to run on |
| `DEBUG` | `false` | Set `true` during development |
| `WHATSAPP_VERIFY_TOKEN` | — | Meta webhook verification token |
| `WHATSAPP_ACCESS_TOKEN` | — | Meta API access token |

**To start fresh:**
```bash
del vendorvault.db    # Windows
rm vendorvault.db     # macOS / Linux
python seed.py
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

**Results:**
```
21 passed in 0.03s
```

Tests cover: single items, comma/and/n separators, word quantities (two, three), digit quantities, 3x suffix notation, customer name extraction (for/from/parentheses patterns), typo tolerance (noddles→Noodles, chiken→Chicken), noise word stripping, greeting handling, no-menu fallback, empty input, and output shape validation.

---

## Evaluation

### What works end-to-end
- Place an order → cash-in-hand increases immediately
- Log a purchase → stock level updates, cash-in-hand decreases
- Log a payout → cash-in-hand decreases
- WhatsApp message → parsed order stored with customer name and line items
- Daily/weekly/monthly reports pull from actual transaction data
- Profit margins calculated from real purchase costs, not hardcoded estimates

### Parser accuracy
Tested against realistic WhatsApp message patterns:

| Input | Expected | Result |
|-------|----------|--------|
| `2 veg noddles` | Veg Noodles ×2 | ✓ |
| `3 chiken 65` | Chicken 65 ×3 | ✓ |
| `two egg fried rice` | Egg Fried Rice ×2 | ✓ |
| `3 egg fried rice and 2 chicken noodles` | 2 items | ✓ |
| `2 veg noodles n 1 egg rice` | 2 items | ✓ |
| `plz send 3 chiken 65 n 2 veg noddles from Rahul` | customer=Rahul, 2 items | ✓ |
| `hi can i get 2 veg noodles` | Veg Noodles ×2 | ✓ |
| `2 unicorn soup` | unrecognized | ✓ |

### Known limitations
- SQLite is single-writer — fine for a single-restaurant, single-user setup. A multi-location or multi-staff deployment would need PostgreSQL.
- WhatsApp webhook requires a public URL. For local use, ngrok works. For production, deploy to a cloud host.
- No user authentication — this is designed to run on a private network or a single-user device.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Stats, chart data, recent orders |
| GET / POST | `/api/orders` | List or place an order |
| DELETE | `/api/orders/:id` | Delete an order |
| GET | `/api/menu` | Menu grouped by category |
| POST | `/api/menu/categories` | Add a category |
| POST | `/api/menu/items` | Add a menu item |
| PUT | `/api/menu/items/:id` | Edit a menu item |
| DELETE | `/api/menu/categories/:id` | Delete a category |
| DELETE | `/api/menu/items/:id` | Delete a menu item |
| GET | `/api/purchases` | Purchases by category |
| POST | `/api/purchases/categories` | Add a purchase category |
| POST | `/api/purchases/items` | Log a purchase |
| POST | `/api/purchases/bulk` | Log multiple purchases at once |
| DELETE | `/api/purchases/categories/:id` | Delete a purchase category |
| DELETE | `/api/purchases/items/:id` | Delete a purchase |
| GET | `/api/finance` | Full financial summary |
| GET | `/api/finance/weekly-cycle` | Weekly cycle breakdown |
| GET | `/api/finance/end-of-day` | End-of-day report (`?date=YYYY-MM-DD`) |
| PUT | `/api/finance/cash` | Correct cash-in-hand manually |
| GET / POST | `/api/expenses` | List or add a payout |
| DELETE | `/api/expenses/:id` | Delete a payout |
| GET | `/api/stock` | Stock levels by category |
| GET | `/api/reports` | Combined daily + weekly + monthly |
| GET | `/api/reports/daily` | Daily report (`?date=YYYY-MM-DD`) |
| GET | `/api/reports/weekly` | Weekly report (`?start=&end=`) |
| GET | `/api/reports/monthly` | Monthly report (`?month=YYYY-MM`) |
| GET | `/api/profits` | Profit margins by menu item |
| GET | `/api/cost-analysis` | Spend by purchase category |
| GET / PUT | `/api/settings` | Read or update settings |
| GET | `/api/network-info` | Local IP and port for phone access |
| GET | `/api/whatsapp/config` | WhatsApp integration config |
| PUT | `/api/whatsapp/config` | Update WhatsApp config |
| GET | `/api/whatsapp/webhook` | Meta webhook verification |
| POST | `/api/whatsapp/webhook` | Incoming message handler |
| POST | `/api/whatsapp/parse` | Parse a free-text message into JSON |
| GET | `/api/whatsapp/messages` | Recent parsed messages |

---

## License

MIT — Copyright (c) 2026 Gaurav Singh Thakur

See [LICENSE](LICENSE) for full terms.
