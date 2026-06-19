# VendorVault

I built this to manage my restaurant's day-to-day operations — tracking orders, logging ingredient purchases, watching cash flow, and figuring out which items are actually making money. It runs locally on my laptop and I can open it on my phone over WiFi during service.

Flask backend, single-file React frontend (no build step), SQLite for storage. Nothing fancy, just something that works reliably in a kitchen.


## Quick Start

```bash
pip install flask
python seed.py       # run once — loads the menu and purchase categories
python app.py        # opens on http://localhost:5000
```

To use it on my phone during service, I go to Settings → Network Access to get the local IP.

To start fresh, I delete `vendorvault.db` and run `seed.py` again.


## What It Does

**Dashboard** — first thing I see when I open it. Shows today's revenue, this week, this month, an hourly chart, top sellers, and recent orders.

**Orders** — I tap items off the menu grid, set quantities, type the customer name, and place the order. Works fine on mobile. I can also backdate an order if I forgot to log something earlier.

**WhatsApp** — I wired up Meta's WhatsApp Business webhook so incoming messages get parsed automatically. The parser reads free-text order messages and pulls out item names, quantities, and the customer name — even with typos and informal phrasing like "2 veg noddles n 1 chiken 65 for Rahul". I can also hit `POST /api/whatsapp/parse` directly to test it without needing a live WhatsApp connection.

**Purchases** — I log every vendor purchase here by category (chicken, eggs, oil, etc.) with quantity, unit, and price. There's a bulk entry mode for restocking days when I'm buying a lot at once.

**Finance** — shows live cash-in-hand that updates with every order, purchase, and payout. My weekly cycle runs Thursday through Sunday. On Monday I pull the excess over $400 and keep $400 as the starting float for the next week. There's also an end-of-day report with item-level breakdowns.

**Stock** — current inventory levels per purchase category, updated whenever I log a purchase.

**Payouts** — staff wages, miscellaneous expenses, anything I pay out. Gets deducted from cash-in-hand automatically.

**Reports** — daily, weekly, and monthly summaries with revenue, cost, profit, and a breakdown by item and source.

**Profits** — overall margin, profit per product, revenue vs cost. Helps me see what's worth keeping on the menu.

**Cost Analysis** — spending grouped by purchase category. Good for seeing where the money actually goes.

**Settings** — business name, contact info, currency, starting cash balance.


## File Layout

```
app.py                Flask server — registers all blueprints and handles startup
database.py           Re-exports everything from db/ so old imports don't break
db/                   All database logic, split by what it does:
  connection.py         SQLite connection setup
  schema.py             Creates all the tables on first run
  menu.py               Menu categories and items
  orders.py             Creating and fetching orders
  purchases.py          Purchases, categories, and stock levels
  expenses.py           Expenses and payouts
  reports.py            Daily, weekly, monthly reports; profits; cost analysis
  finance.py            Cash-in-hand, weekly cycle, finance summary
  dashboard.py          Aggregated dashboard stats
  settings.py           App settings (key-value store)
routes/               One blueprint file per feature
services/
  order_parser.py       Free-text → structured ParsedOrder, no external deps
tests/
  test_order_parser.py  21 tests for the WhatsApp order parser
index.html            React frontend — everything in one file, no build needed
seed.py               Loads the starting menu and purchase categories
seed_orders.py        Generates sample orders for testing
seed_purchases.py     Generates sample purchase data for testing
requirements.txt      Just Flask
```


## API Endpoints

| Method | Path | What it does |
|--------|------|-------------|
| GET | `/api/dashboard` | Today/week/month stats, hourly chart, recent orders |
| GET, POST | `/api/orders` | All orders, or place a new one |
| DELETE | `/api/orders/:id` | Delete an order |
| GET | `/api/menu` | Menu grouped by category |
| POST | `/api/menu/categories` | Add a category |
| POST | `/api/menu/items` | Add a menu item |
| PUT | `/api/menu/items/:id` | Edit a menu item |
| DELETE | `/api/menu/categories/:id` | Delete a category and everything in it |
| DELETE | `/api/menu/items/:id` | Delete a menu item |
| GET | `/api/purchases` | Purchases grouped by category |
| POST | `/api/purchases/categories` | Add a purchase category |
| POST | `/api/purchases/items` | Log a purchase |
| POST | `/api/purchases/bulk` | Log multiple purchases at once |
| DELETE | `/api/purchases/categories/:id` | Delete a purchase category |
| DELETE | `/api/purchases/items/:id` | Delete a purchase record |
| GET | `/api/finance` | Full financial summary with live cash-in-hand |
| GET | `/api/finance/weekly-cycle` | This week's Thu–Sun cycle |
| GET | `/api/finance/end-of-day` | End-of-day report (add `?date=YYYY-MM-DD`) |
| PUT | `/api/finance/cash` | Manually correct cash-in-hand |
| GET, POST | `/api/expenses` | List or add a payout |
| DELETE | `/api/expenses/:id` | Delete a payout |
| GET | `/api/stock` | Current stock levels |
| GET | `/api/reports` | Daily + weekly + monthly combined |
| GET | `/api/reports/daily` | Daily report (`?date=`) |
| GET | `/api/reports/weekly` | Weekly report (`?start=&end=`) |
| GET | `/api/reports/monthly` | Monthly report (`?month=`) |
| GET | `/api/profits` | Profit margins by product |
| GET | `/api/cost-analysis` | Purchase costs by category |
| GET, PUT | `/api/settings` | Read or update settings |
| GET | `/api/network-info` | Local IP and port for phone access |
| GET | `/api/whatsapp/config` | WhatsApp integration settings |
| PUT | `/api/whatsapp/config` | Update WhatsApp settings |
| GET | `/api/whatsapp/webhook` | Meta webhook verification |
| POST | `/api/whatsapp/webhook` | Incoming WhatsApp message handler |
| POST | `/api/whatsapp/parse` | Parse a free-text order message into JSON |
| GET | `/api/whatsapp/messages` | Recent parsed WhatsApp messages |


## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Port to run on |
| `DEBUG` | `false` | Set to `true` locally when I'm developing |


## How Cash-in-Hand Works

I compute it live every time:

```
Cash = Starting Balance + Order Revenue − Purchases − Payouts
```

Every order adds to it. Every purchase or payout takes from it. If the number drifts from my actual count, I correct it from the Finance tab — the system adjusts the starting balance to keep the math right.


## Weekly Cash Cycle

My week runs Thursday through Sunday. On Monday I count the cash, pull everything over $400, and put $400 back as the float for next week. The Finance → Weekly Cycle tab tracks this day by day.


## License

MIT — Gaurav Singh Thakur, 2026
