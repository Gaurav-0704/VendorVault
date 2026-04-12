# VendorVault

Restaurant management system for tracking orders, purchases, finances, and profits. Built for daily kitchen operations — handles walk-in, call, and WhatsApp orders, tracks ingredient costs, calculates margins, and generates end-of-day reports.

Flask backend, React frontend (single-file, no build step), SQLite database. Runs locally and works on your phone over WiFi.

Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.


## Quick Start

```bash
pip install flask
python seed.py       # first time only — loads menu + purchase categories
python app.py        # starts on http://localhost:5000
```

For phone access, open Settings > Network Access to get your local IP address.

To start fresh, delete `vendorvault.db` and run `seed.py` again.


## What It Does

**Dashboard** — today/week/month stats, hourly revenue chart, top-selling items, recent orders at a glance.

**Orders** — tap items from the menu grid, set quantities, enter customer name, place order. Works on desktop and mobile. Supports backdating orders to a specific date.

**Purchases** — log vendor purchases by category (chicken, eggs, rice, etc.) with quantities, units, and prices. Bulk entry mode for restocking days.

**Finance** — live cash-in-hand that updates automatically with every order, purchase, and payout. Weekly cash cycle (Thu–Sun active, collect excess Monday, keep $400 for next week). End-of-day reports with item-level breakdowns. Transaction ledger.

**Stock** — current inventory levels by purchase category, updated when purchases are logged.

**Payouts** — track miscellaneous expenses and staff payouts. Automatically deducted from cash-in-hand.

**Reports** — daily, weekly, and monthly revenue/expense/profit summaries with item breakdowns and source tracking.

**Profits** — overall margin percentage, profit per product, revenue vs cost breakdown.

**Cost Analysis** — spending grouped by purchase category, average cost per item.

**Settings** — business name, contact info, currency, starting cash balance.


## Files

```
app.py             Flask routes and server entry point
database.py        All SQLite queries and business logic
index.html         React frontend (single file, no build step)
seed.py            One-time menu and purchase category loader
seed_orders.py     Sample order data for testing
seed_purchases.py  Sample purchase data for testing
requirements.txt   Python dependencies (just Flask)
.gitignore         Ignores database, cache, env files
```


## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard` | Today/week/month stats, charts, recent orders |
| GET, POST | `/api/orders` | List all orders or create a new one |
| DELETE | `/api/orders/:id` | Delete an order |
| GET | `/api/menu` | Menu categories with items |
| POST | `/api/menu/categories` | Add a menu category |
| POST | `/api/menu/items` | Add a menu item |
| PUT | `/api/menu/items/:id` | Update a menu item |
| DELETE | `/api/menu/categories/:id` | Delete a category and its items |
| DELETE | `/api/menu/items/:id` | Delete a menu item |
| GET | `/api/purchases` | Purchases grouped by category |
| POST | `/api/purchases/categories` | Add a purchase category |
| POST | `/api/purchases/items` | Add a purchase item |
| POST | `/api/purchases/bulk` | Bulk-add purchase items |
| DELETE | `/api/purchases/categories/:id` | Delete a purchase category |
| DELETE | `/api/purchases/items/:id` | Delete a purchase item |
| GET | `/api/finance` | Financial overview with live cash-in-hand |
| GET | `/api/finance/weekly-cycle` | Current week's Thu–Sun cycle data |
| GET | `/api/finance/end-of-day` | End-of-day report (accepts `?date=`) |
| PUT | `/api/finance/cash` | Manually correct cash-in-hand |
| GET, POST | `/api/expenses` | List or add payouts/expenses |
| DELETE | `/api/expenses/:id` | Delete an expense |
| GET | `/api/stock` | Current stock levels |
| GET | `/api/reports` | Combined daily + weekly + monthly |
| GET | `/api/reports/daily` | Daily report (accepts `?date=`) |
| GET | `/api/reports/weekly` | Weekly report (accepts `?start=&end=`) |
| GET | `/api/reports/monthly` | Monthly report (accepts `?month=`) |
| GET | `/api/profits` | Profit margins by product |
| GET | `/api/cost-analysis` | Costs grouped by purchase category |
| GET, PUT | `/api/settings` | Read or update app settings |
| GET | `/api/network-info` | Local IP and access URLs |


## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Server port |
| `DEBUG` | `true` | Flask debug mode |


## How Cash-in-Hand Works

Cash-in-hand is computed in real time:

```
Cash = Starting Balance + Order Revenue - Purchases - Payouts
```

Every order increases it. Every purchase or payout decreases it. You can manually correct it from the Finance tab if the number drifts from your actual count — the system adjusts the starting balance to keep the math clean.


## Weekly Cash Cycle

The weekly cycle runs Thursday through Sunday. On Monday, take the excess over $400 and keep $400 as starting cash for the next week. The Finance > Weekly Cycle tab tracks daily revenue, purchases, and payouts within each cycle.


## License

MIT
