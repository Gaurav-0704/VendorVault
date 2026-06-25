# VendorVault

I built VendorVault to solve a specific frustration: I was running a small restaurant and had no clear picture of where my money actually went. I knew my revenue. I didn't know my real profit. I couldn't answer "how much did I spend on chicken this week?" without digging through paper receipts. And when customers ordered on WhatsApp, I was copying messages by hand into a notebook.

So I built this. It runs on my laptop, opens on my phone over WiFi during service, and gives me the numbers I actually care about in real time.

---

## What Makes VendorVault Different

Most restaurant systems are built around sales. VendorVault is built around the full picture: what I spent, what I earned, and what's left. Here's why it's different from generic POS software:

### WhatsApp-Native Order Processing
Most POS systems expect orders to come through a terminal. My customers text me on WhatsApp in mixed Hindi-English with typos: *"bhai 2 veg noddles n 1 chiken 65 bhej do for Rahul"*. VendorVault parses that message and turns it into a structured order — customer name, items, quantities — without me doing anything. The parser handles typos, informal separators ("n", "and", "+"), word numbers ("two", "three"), and greeting noise ("hi", "please", "bhai"). No external ML libraries — just Python's stdlib `re` and `difflib`.

### Purchase-First Restaurant Management
I log every purchase — chicken, eggs, oil, packaging — with quantity and price. VendorVault tracks my actual cost of goods, so when I look at a menu item's profit, it's based on what I actually paid, not a guess. Most POS systems skip this entirely.

### Real Cash-in-Hand Tracking
The Finance screen shows one number: how much cash should be in my drawer right now. Every order adds to it. Every purchase and payout subtracts from it. If the number drifts from my actual count, I correct it in one tap — the system adjusts the starting balance to keep the math right.

### Weekly Cycle Awareness
My service week runs Thursday through Sunday. On Monday I count the drawer, pull the excess over a target float, and bank it. VendorVault models this cycle — it shows each day's movement, the expected pullout amount, and the starting float for next week.

### Inventory That Actually Updates
When I log a purchase, stock goes up. When I confirm an order, stock goes down. I don't manage inventory in a separate screen — it falls out naturally from what I've bought and sold.

---

## What VendorVault Does

**Dashboard**
First thing I see when I open the app: today's revenue, this week, this month, an hourly revenue chart, top-selling items, and recent orders. Enough to know if service is going well without digging.

**Orders**
Tap items on a menu grid, set quantities, enter the customer name, place the order. Works fine on mobile. I can also backdate orders I forgot to log during a busy service.

**WhatsApp Order Parsing**
Meta's WhatsApp Business webhook pushes incoming messages to `/api/whatsapp/webhook`. I parse the free text with a pure-Python parser. It extracts the customer name, matches item names even with typos, and stores the structured order. I can also call `POST /api/whatsapp/parse` directly to test any message without needing a live WhatsApp connection.

Example input → output:
```
Input:  "plz send 3 chiken 65 n 2 veg noddles from Rahul"
Output: { customer: "Rahul", lines: [{ item: "Chicken 65", qty: 3 }, { item: "Veg Noodles", qty: 2 }] }
```

**Purchases**
Every vendor purchase goes here: category (chicken, eggs, oil), quantity, unit, price. Bulk entry mode for restocking days. All of it feeds into cost calculations downstream.

**Finance**
Live cash-in-hand, updated automatically. Also shows a weekly cycle view (Thu–Sun), an end-of-day breakdown, and a full finance summary. If the drawer count doesn't match the system, I correct it from here.

**Stock**
Current inventory levels per purchase category. Updates automatically when purchases or orders are logged.

**Payouts / Expenses**
Staff wages, miscellaneous expenses. Anything I pay out gets subtracted from cash-in-hand.

**Reports**
Daily, weekly, and monthly summaries — revenue, cost, profit, per-item breakdown.

**Profits**
Overall margin, profit per menu item, revenue vs cost. This is where I decide what's worth keeping on the menu.

**Cost Analysis**
Spending grouped by purchase category. Useful for seeing where the money actually goes week-over-week.

**Settings**
Business name, contact info, currency, starting cash balance.

---

## Architecture

```
Frontend     Single-page React app in index.html — no build step, no node_modules
Backend      Flask (Python 3.9+), one blueprint per feature area
Database     SQLite with WAL mode and foreign keys
Parser       Pure stdlib — re + difflib, no external NLP dependencies
Tests        pytest, 21 tests for the WhatsApp order parser
Deploy       Docker + gunicorn, Railway-compatible via Procfile and railway.toml
```

**File layout:**
```
app.py                  Flask entry point — registers blueprints, sets DEBUG from env
database.py             Compatibility shim — re-exports everything from db/
db/
  connection.py         SQLite setup, WAL mode, context manager
  schema.py             Creates all tables on first run
  menu.py               Menu categories and items
  orders.py             Order creation and retrieval
  purchases.py          Purchase logging, categories, stock levels
  expenses.py           Expenses and payouts
  reports.py            Report queries (daily, weekly, monthly)
  finance.py            Cash-in-hand, weekly cycle, end-of-day
  dashboard.py          Aggregated stats for the dashboard
  settings.py           Key-value settings store
routes/                 One blueprint file per feature
services/
  order_parser.py       Free-text → ParsedOrder dataclass, no external deps
tests/
  test_order_parser.py  Parser tests — clean inputs, typos, edge cases, messy messages
index.html              Full React frontend
seed.py                 Loads starting menu and purchase categories
Dockerfile              For Docker and Railway deployments
docker-compose.yml      One-command local setup
Makefile                Common dev commands (make run, make test, make setup)
Procfile                For Railway / Heroku
railway.toml            Railway deployment config
.env.example            Environment variable reference
requirements.txt        Flask + gunicorn
```

---

## Quick Setup (One Command)

```bash
# Clone and start with Docker
git clone https://github.com/Gaurav-0704/VendorVault.git
cd VendorVault
docker compose up
```

Open `http://localhost:5000`. Data is stored in a named Docker volume — it survives container restarts.

Or use Make:
```bash
make setup    # installs deps, seeds the database, starts the server
```

---

## Manual Installation

### Prerequisites
- Python 3.9 or later
- pip

No Node, no Docker, no database server required.

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/Gaurav-0704/VendorVault.git
cd VendorVault

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed the database (run once — creates the SQLite file and loads starting data)
python seed.py

# 4. Start the server
python app.py
```

Open `http://localhost:5000`. To access it from your phone on the same WiFi network, go to **Settings → Network Access** in the app to get your local IP.

### Environment Variables

Copy `.env.example` to `.env` and fill in your values. The `.env` file is gitignored.

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Port to run the server on |
| `DEBUG` | `false` | Set to `true` for development (auto-reload, detailed errors) |
| `WHATSAPP_VERIFY_TOKEN` | — | Token for Meta webhook verification |
| `WHATSAPP_ACCESS_TOKEN` | — | Meta API access token for sending messages |
| `WHATSAPP_PHONE_NUMBER_ID` | — | Your WhatsApp Business phone number ID |

Set them before running:
```bash
# Windows
set DEBUG=true && python app.py

# macOS/Linux
DEBUG=true python app.py
```

### Running Tests

```bash
python -m pytest tests/ -v
```

All 21 parser tests should pass. They cover clean inputs, typos, mixed separators, word quantities, customer name extraction, and edge cases.

### Starting Over

```bash
make clean    # deletes the database
make seed     # recreates and seeds it
make run      # start the server
```

Or manually:
```bash
del vendorvault.db      # Windows
rm vendorvault.db       # macOS/Linux
python seed.py
python app.py
```

---

## Deploying to Railway

Railway is the easiest way to host this publicly. Here's the full process:

### 1. Create a Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project → Deploy from GitHub repo**
3. Select your fork of `VendorVault`
4. Railway will detect the `Dockerfile` and build automatically

### 2. Set Environment Variables

In your Railway project → **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `PORT` | `5000` |
| `DEBUG` | `false` |
| `WHATSAPP_VERIFY_TOKEN` | your chosen verify token |
| `WHATSAPP_ACCESS_TOKEN` | from Meta Developer Portal |
| `WHATSAPP_PHONE_NUMBER_ID` | from Meta Developer Portal |

Railway injects `PORT` automatically in some plans — set it explicitly to avoid conflicts.

### 3. Set Up a Domain

In Railway → your service → **Settings → Networking**, click **Generate Domain** to get a public URL like `vendorvault-production.up.railway.app`.

You'll need this URL for the WhatsApp webhook.

### 4. Configure the WhatsApp Webhook

In the [Meta Developer Portal](https://developers.facebook.com):
1. Go to your app → **WhatsApp → Configuration**
2. Set **Webhook URL** to: `https://your-railway-domain/api/whatsapp/webhook`
3. Set **Verify Token** to whatever you put in `WHATSAPP_VERIFY_TOKEN`
4. Subscribe to the `messages` webhook field

### 5. Verify the Deployment

```bash
curl https://your-railway-domain/api/dashboard
```

Should return JSON with today's stats. If you get a 502, check the Railway build logs — the most common issue is a missing environment variable.

### Notes on SQLite on Railway

Railway's filesystem is ephemeral — the SQLite database resets on each deploy. For a production setup where you need data to persist across deploys, you have two options:

1. **Railway Volume** — attach a persistent volume to `/app/data` in your Railway service settings. This is the simplest fix and works well for a single-instance setup.
2. **PostgreSQL** — Railway has a first-party PostgreSQL plugin. Migrating to Postgres would require replacing SQLite queries with a Postgres client (psycopg2) and updating the connection logic in `db/connection.py`. That's a future improvement — for now, a Railway volume is enough.

---

## WhatsApp Business Setup

To receive real WhatsApp orders, you need a Meta WhatsApp Business API account. Here's how I set it up:

### 1. Create a Meta Developer Account

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create a new app → **Business** type
3. Add the **WhatsApp** product to your app

### 2. Get Your Credentials

In your app dashboard → **WhatsApp → API Setup**:

- **Phone Number ID** → set as `WHATSAPP_PHONE_NUMBER_ID`
- **Access Token** (temporary) → set as `WHATSAPP_ACCESS_TOKEN`

For a permanent token, create a System User in Business Manager and generate a token there.

### 3. Configure the Webhook

1. Your server must be publicly accessible (Railway URL, or ngrok for local dev)
2. In **WhatsApp → Configuration → Webhooks**:
   - Webhook URL: `https://your-domain/api/whatsapp/webhook`
   - Verify Token: any string you choose — set the same value as `WHATSAPP_VERIFY_TOKEN`
3. Click **Verify and Save**, then subscribe to the `messages` field

### 4. Test the Parser Without WhatsApp

You don't need a live WhatsApp connection to test the parser:

```bash
curl -X POST http://localhost:5000/api/whatsapp/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "2 veg noddles n 1 chiken 65 for Rahul"}'
```

Response:
```json
{
  "customer": "Rahul",
  "lines": [
    {"item": "Veg Noodles", "quantity": 2, "confidence": 0.89},
    {"item": "Chicken 65", "quantity": 1, "confidence": 0.82}
  ],
  "raw_text": "2 veg noddles n 1 chiken 65 for Rahul",
  "unrecognized": []
}
```

### 5. Test Mode vs Production

During development, Meta restricts your WhatsApp number to test contacts only. You can send and receive messages with numbers you've explicitly added in the API Setup tab. To go live, submit your app for Meta's Business Verification review.

---

## Razorpay Setup *(planned)*

Razorpay payment collection is on the roadmap. When implemented, here's how it will work:

### What It Will Do
- Customers receive a payment link via WhatsApp after their order is parsed
- Payments are confirmed via Razorpay webhooks
- Order status updates automatically on payment

### Setup (when available)

1. Create a [Razorpay account](https://razorpay.com) and get your API keys from the Dashboard
2. Add to your environment:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

3. In Razorpay Dashboard → **Settings → Webhooks**, add:
   - URL: `https://your-domain/api/payments/webhook`
   - Subscribe to `payment.captured` and `payment.failed`

**Test vs Production credentials:**
- Keys starting with `rzp_test_` hit the test environment — no real money moves
- Keys starting with `rzp_live_` are production — real payments
- Never commit either to git. Always use environment variables.

**For real-world use:** you must provide your own Razorpay credentials. VendorVault doesn't include any shared keys.

---

## User Workflow

If you're setting up VendorVault for the first time, do it in this order:

1. **Configure Settings** — business name, currency, starting cash balance
2. **Add Purchase Categories** — chicken, eggs, oil, packaging — whatever you buy
3. **Add Menu Categories** — starters, mains, beverages, etc.
4. **Add Menu Items** — with selling price and cost price
5. **Log Opening Stock** — use Purchases to set your starting inventory levels
6. **Set Up WhatsApp** *(optional)* — configure webhook in Meta Developer Portal
7. **Start Logging Orders** — via the Orders screen or WhatsApp
8. **Log Purchases as You Restock** — stock and cash-in-hand update automatically
9. **Log Payouts** — staff wages, miscellaneous expenses
10. **Check Finance Daily** — verify cash-in-hand matches your actual drawer count
11. **Review Reports Weekly** — profits, cost analysis, top sellers

---

## API Endpoints

| Method | Path | What it does |
|--------|------|-------------|
| GET | `/api/dashboard` | Today/week/month stats, hourly chart, recent orders |
| GET, POST | `/api/orders` | List orders or place a new one |
| DELETE | `/api/orders/:id` | Delete an order |
| GET | `/api/menu` | Menu grouped by category |
| POST | `/api/menu/categories` | Add a category |
| POST | `/api/menu/items` | Add a menu item |
| PUT | `/api/menu/items/:id` | Edit a menu item |
| DELETE | `/api/menu/categories/:id` | Delete a category |
| DELETE | `/api/menu/items/:id` | Delete a menu item |
| GET | `/api/purchases` | Purchases grouped by category |
| POST | `/api/purchases/categories` | Add a purchase category |
| POST | `/api/purchases/items` | Log a purchase |
| POST | `/api/purchases/bulk` | Log multiple purchases at once |
| DELETE | `/api/purchases/categories/:id` | Delete a purchase category |
| DELETE | `/api/purchases/items/:id` | Delete a purchase record |
| GET | `/api/finance` | Full financial summary with live cash-in-hand |
| GET | `/api/finance/weekly-cycle` | This week's Thu–Sun cycle breakdown |
| GET | `/api/finance/end-of-day` | End-of-day report (add `?date=YYYY-MM-DD`) |
| PUT | `/api/finance/cash` | Manually correct cash-in-hand |
| GET, POST | `/api/expenses` | List or add a payout |
| DELETE | `/api/expenses/:id` | Delete a payout |
| GET | `/api/stock` | Current stock levels by category |
| GET | `/api/reports` | Combined daily + weekly + monthly |
| GET | `/api/reports/daily` | Daily report (`?date=YYYY-MM-DD`) |
| GET | `/api/reports/weekly` | Weekly report (`?start=&end=`) |
| GET | `/api/reports/monthly` | Monthly report (`?month=YYYY-MM`) |
| GET | `/api/profits` | Profit margins by menu item |
| GET | `/api/cost-analysis` | Purchase spending by category |
| GET, PUT | `/api/settings` | Read or update app settings |
| GET | `/api/network-info` | Local IP and port for phone access |
| GET | `/api/whatsapp/config` | WhatsApp integration settings |
| PUT | `/api/whatsapp/config` | Update WhatsApp settings |
| GET | `/api/whatsapp/webhook` | Meta webhook verification handshake |
| POST | `/api/whatsapp/webhook` | Incoming WhatsApp message handler |
| POST | `/api/whatsapp/parse` | Parse a free-text order message into JSON |
| GET | `/api/whatsapp/messages` | Recent parsed WhatsApp messages |

---

## How Cash-in-Hand Works

I compute it live every time from the raw transactions — nothing is cached:

```
Cash = Starting Balance
     + Sum of all order revenue
     − Sum of all purchase costs
     − Sum of all payouts/expenses
```

If my drawer count doesn't match (someone handed back change I didn't log, or I made a cash run I forgot), I correct it from the Finance tab. The system adjusts the starting balance so the formula stays right.

---

## Weekly Cash Cycle

My service week runs Thursday through Sunday. On Monday I count the drawer, pull everything over my target float (currently ₹400), and bank the rest. The **Finance → Weekly Cycle** tab tracks this:
- Each day's opening balance, inflows, outflows
- Running total through the week
- Suggested pullout amount on Monday

---

## Troubleshooting

**Port already in use**
```bash
PORT=8080 python app.py
```

**Database errors on startup**
Delete the database and re-seed:
```bash
make clean && make seed
```

**WhatsApp webhook not receiving messages**
The webhook endpoint needs to be publicly accessible. For local dev, use [ngrok](https://ngrok.com):
```bash
ngrok http 5000
# Use the https://xxxxx.ngrok.io URL as your webhook in Meta Developer Portal
```

**Phone can't connect over WiFi**
Make sure both devices are on the same network. Get the LAN IP from **Settings → Network Access** in the app. If your laptop is on a VPN, disconnect it — VPNs usually block LAN traffic.

**Railway deploy not persisting data**
Attach a Railway Volume to `/app/data` in your service settings. Without it, the SQLite file resets on each deploy.

---

## Production Readiness Checklist

Before going live:

- [ ] `DEBUG` is set to `false` (or not set — it defaults to false)
- [ ] `PORT` is configured for your hosting environment
- [ ] Starting cash balance is set correctly in Settings
- [ ] Menu items are loaded with correct prices and costs
- [ ] Purchase categories match your actual vendor categories
- [ ] WhatsApp `WHATSAPP_VERIFY_TOKEN` is set and matches Meta Portal
- [ ] WhatsApp `WHATSAPP_ACCESS_TOKEN` is set with a non-expiring system user token
- [ ] Railway Volume attached at `/app/data` (for persistent storage)
- [ ] Custom domain or Railway-generated domain is configured
- [ ] Test a full order flow end-to-end — WhatsApp message → parsed order → Finance updated
- [ ] Run `python -m pytest tests/` — all tests green

---

## License

MIT — Gaurav Singh Thakur, 2026
