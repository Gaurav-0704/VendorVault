# VendorVault

A full-stack sales and profit tracking web application built for small businesses. Handles order management, ingredient cost tracking, real-time profit calculations, expense logging, and WhatsApp Business integration.

Designed primarily for cloud kitchens, restaurants, and food businesses — but works for any retail or service-based operation.

---

## Features

- **Dashboard** — Live overview of daily, weekly, and monthly revenue, profit, and order counts. Hourly sales chart and top-selling items.
- **Order Management** — Tap-to-add order builder with real-time profit preview. Supports multiple sources: walk-in, phone call, WhatsApp, online.
- **Menu Management** — Add, edit, toggle, and delete menu items. Each item shows selling price, cost, profit, and margin with a full ingredient-level cost breakdown.
- **Purchase Tracker** — Log all ingredient and packaging purchases. Update prices anytime and menu costs auto-recalculate across every item. Add new items and categories on the fly.
- **Reports & Analytics** — Daily, weekly, and monthly reports with revenue vs. profit charts. Item performance ranking and profit margin analysis. CSV export.
- **Expense Tracker** — Record non-ingredient costs like rent, gas, marketing, labor, and utilities.
- **WhatsApp Integration** — Manual order entry with WhatsApp source tagging (works now). Meta WhatsApp Business API webhook support built in for future auto-order intake.
- **Settings** — Configurable business name, type, currency, and tax rate.

---

## Tech Stack

- **Backend:** Python 3, Flask, SQLite
- **Frontend:** React 18 (via CDN), vanilla CSS
- **Database:** SQLite with WAL mode (zero setup, file-based)
- **No external services required** — runs 100% locally

---

## Installation

### Prerequisites

- Python 3.8 or higher installed on your system
- pip (comes with Python)
- A modern web browser (Chrome, Edge, Firefox, Safari)

### Step 1 — Download the project

Clone the repo or download and extract the ZIP:

```bash
git clone https://github.com/Gaurav-0704/VendorVault.git
cd VendorVault
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs Flask (the only dependency).

If you're on Linux/Mac and get a permission error, use:

```bash
pip install -r requirements.txt --break-system-packages
```

### Step 3 — Run the application

```bash
python start.py
```

On first run, this will:
1. Create the `data/` folder automatically
2. Set up the SQLite database with all tables
3. Seed your menu items, purchase prices, and default settings
4. Start the web server

### Step 4 — Open in browser

Go to **http://localhost:5000**

That's it. No environment variables, no Docker, no cloud accounts needed.

---

## Usage

### Adding Orders

1. Go to **Orders** from the sidebar
2. Fill in customer name and source (walk-in, call, WhatsApp)
3. Tap menu items to add them to the cart
4. Use + / − to adjust quantities
5. Review the live profit calculation at the bottom
6. Click **Place Order**

### Updating Purchase Prices

1. Go to **Purchases** from the sidebar
2. Click any category to expand it
3. Edit the quantity or price fields directly — changes save on blur
4. Menu item costs recalculate automatically
5. Use **+ Add item** inside any category to add new ingredients
6. Use **+ Category** at the top to create new groups

### Viewing Reports

1. Go to **Reports** from the sidebar
2. Switch between Daily, Weekly, and Monthly tabs
3. Click **Export CSV** to download order data as a spreadsheet

### Setting Up WhatsApp (Optional)

1. Go to **WhatsApp** from the sidebar
2. For now, manually enter WhatsApp orders through the Orders page with "WhatsApp" as the source
3. To enable the auto-receive API later, follow the setup guide on the page to connect your Meta Business account

---

## Project Structure

```
VendorVault/
├── start.py              # Entry point — run this to launch
├── app.py                # Flask app factory
├── config.py             # Port, database path, secret key
├── database.py           # Schema definitions and seed data
├── requirements.txt      # Python dependencies
├── .gitignore            # Git ignore rules
├── routes/
│   ├── __init__.py       # Blueprint registration
│   ├── dashboard.py      # Dashboard + quick stats API
│   ├── orders.py         # Order CRUD + CSV export
│   ├── menu.py           # Menu CRUD + cost breakdown API
│   ├── purchases.py      # Purchase CRUD + cost recalculation
│   ├── reports.py        # Daily/weekly/monthly reports
│   ├── expenses.py       # Expense tracking
│   ├── whatsapp.py       # WhatsApp webhook + message parser
│   └── settings.py       # Business settings
├── templates/
│   └── index.html        # React frontend (single page app)
├── static/               # Static assets (CSS, JS, images)
└── data/                 # SQLite database (auto-created, gitignored)
```

---

## Customization

### Changing the Menu

Edit the seed data in `database.py` under the `seed_default_data()` function. Modify item names, prices, and cost formulas. Or just use the Menu page in the app to add/edit items through the UI.

### Changing Purchase Items

Same approach — either edit `database.py` for the initial seed, or use the Purchases page in the app. The cost recalculation logic lives in `routes/purchases.py`.

### Adding New API Endpoints

Create a new file in `routes/`, define a Flask Blueprint, and register it in `routes/__init__.py`.

### Switching to a Cloud Database

Replace the SQLite connection in `database.py` with a PostgreSQL or MySQL connector. The SQL is standard and should work with minimal changes.

---

## Resetting the Database

To start fresh with a clean database:

**Windows:**
```cmd
cd VendorVault
rmdir /s /q data
python start.py
```

**Mac/Linux:**
```bash
cd VendorVault
rm -rf data
python start.py
```

---

## License

Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.

This software is provided for personal and educational use. Redistribution or commercial use without written permission from the author is prohibited.

---

## Author

**Gaurav Singh Thakur**
GitHub: [@Gaurav-0704](https://github.com/Gaurav-0704)
