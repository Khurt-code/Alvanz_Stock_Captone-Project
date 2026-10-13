# AlvanzStock — Web-Based Inventory & POS System for Alvanz Hardware

<!-- Project entry guide: setup, accounts, frontend build, and high-level app/module connections. -->

A capstone project implementing a web-based inventory management and Point of Sale (POS) system. Built with **Django 6** (Python) and **TailwindCSS**.

## Features

- **Real-time inventory monitoring** — stock updates push instantly over a WebSocket to every open Live Stock screen (and low-stock toasts) as stock-in, stock-out, sales, or returns happen.
- **Stock-in / Stock-out recording** — track incoming and outgoing items with reference numbers and notes.
- **Point of Sale (POS)** — product search, cart, discounts, cash tendering, change computation, and printable receipts.
- **Low-stock alerts** — automatic warning when a product's quantity reaches its minimum stock level.
- **Reports** — sales report (today / last 7 days / this month), inventory report with stock valuation, and sales history.
- **Analytics dashboard** — manager-only KPIs (net sales, profit, margin), sales trend, top products, and category breakdown with live-updating Chart.js charts plus CSV export.
- **Role-based access** — Manager, Cashier, Staff, and Stock Viewer roles; Cashier/Staff get read-only inventory plus POS, while inventory writes stay manager-only.
- **Django Admin** — full management interface at `/admin/`.

## Tech Stack

- Backend: Django 6.1, Django Channels 4 (ASGI/Daphne), SQLite
- Frontend: TailwindCSS 3 (CLI build), vanilla JS + WebSockets, Chart.js (vendored)

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py migrate
./venv/bin/python manage.py seed_data   # optional demo data
./venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000

`runserver` is served by Daphne (ASGI) because `daphne` is in `INSTALLED_APPS`, so the live-stock WebSocket works with no extra server. The default channel layer is in-memory (single process); use Redis for multi-worker deployments.

### Demo accounts (created by `seed_data`)

| Username | Password   | Role    |
|----------|------------|---------|
| admin    | admin123   | Manager |
| cashier  | cashier123 | Cashier |
| staff    | staff123   | Staff   |

## Adding Accounts

There is no in-app user-management page. Add user accounts either through Django Admin or via the shell.

### Via Django Admin (recommended)

1. Start the server: `./venv/bin/python manage.py runserver`
2. Log in at http://127.0.0.1:8000/admin/ (e.g. `admin` / `admin123`)
3. Go to **Users → Add user**, enter a username and password, then click *Save*
4. On the next screen set:
   - **Role** — `Manager`, `Cashier`, `Staff`, or `Stock Viewer` (controls access; Managers own inventory writes and Sales & Reports, Cashier/Staff get read-only inventory plus POS, Stock Viewer sees only Live Stock)
   - **Staff status** / **Superuser status** — check these if the account should also manage Django Admin
   - Optionally first/last name and email

### Via shell

```bash
./venv/bin/python manage.py shell -c "
from accounts.models import User
u = User.objects.create_user('username', password='pass123', role=User.Role.CASHIER)
u.first_name = 'First'
u.last_name = 'Last'
u.save()
"
```

Available roles: `User.Role.MANAGER`, `User.Role.CASHIER`, `User.Role.STAFF`, `User.Role.STOCK_VIEWER`.

### Tailwind

CSS is already compiled to `static/css/output.css`. If you modify templates:

```bash
npm install
npm run build:css     # one-off build
npm run watch:css     # watch for changes
```

## Project Structure

```
alvanzstock/
├── accounts/    # custom user with roles, login
├── inventory/   # categories, products, stock transactions, low-stock
├── pos/         # sales, POS checkout, receipts, reports
├── templates/   # Tailwind-styled templates
└── static/      # compiled Tailwind output
```
