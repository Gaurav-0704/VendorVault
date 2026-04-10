# VendorVault

Simple restaurant management app. Flask backend, React frontend, SQLite database. Runs locally and works on your phone over WiFi too.

## Setup

```bash
pip install flask
python app.py
```

Opens at `http://localhost:5000`. For phone access, check Settings > Network Access for your local IP.

## Features

- **Dashboard** — today/week/month revenue, hourly chart, recent orders
- **Orders** — pick items from the menu, auto-calculates totals
- **Purchases** — track vendor purchases by category with quantities and costs
- **Reports** — daily, weekly, monthly breakdowns
- **Profits** — margin per product, overall profit %
- **Cost Analysis** — purchase spending grouped by category
- **Settings** — business info, currency, network URL for phone access

## Files

```
app.py          — routes and server entry point
database.py     — all sqlite queries
index.html      — react frontend (single file, no build step)
requirements.txt
.gitignore
```

## API

| Method | Path | What it does |
|--------|------|-------------|
| GET | `/api/dashboard` | Stats + charts |
| GET/POST | `/api/orders` | List or create orders |
| DELETE | `/api/orders/:id` | Remove order |
| GET | `/api/menu` | Menu categories + items |
| POST | `/api/menu/categories` | New category |
| POST | `/api/menu/items` | New item |
| DELETE | `/api/menu/categories/:id` | Remove category |
| DELETE | `/api/menu/items/:id` | Remove item |
| GET | `/api/purchases` | Purchases by category |
| POST | `/api/purchases/categories` | New purchase category |
| POST | `/api/purchases/items` | New purchase item |
| DELETE | `/api/purchases/categories/:id` | Remove category |
| DELETE | `/api/purchases/items/:id` | Remove item |
| GET | `/api/reports` | Daily + weekly + monthly |
| GET | `/api/profits` | Profit per product |
| GET | `/api/cost-analysis` | Cost per category |
| GET/PUT | `/api/settings` | Read/update settings |
| GET | `/api/network-info` | Local IP + URLs |

## Config

| Env var | Default | |
|---------|---------|---|
| `PORT` | `5000` | server port |
| `DEBUG` | `true` | flask debug mode |

## License

MIT
