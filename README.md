# AlvanzStock — Web-Based Inventory & POS System for Alvanz Hardware

A capstone project implementing a web-based inventory management and Point of Sale (POS) system. Built with **Django 6** (Python) and **TailwindCSS**.

## Features

- **Real-time inventory monitoring** — stock updates automatically after every stock-in, stock-out, or sale.
- **Stock-in / Stock-out recording** — track incoming and outgoing items with reference numbers and notes.
- **Point of Sale (POS)** — product search, cart, discounts, cash tendering, change computation, and printable receipts.
- **Low-stock alerts** — automatic warning when a product's quantity reaches its minimum stock level.
- **Reports** — sales report (today / last 7 days / this month), inventory report with stock valuation, and sales history.
- **Role-based access** — Manager, Cashier, and Staff roles.
- **Django Admin** — full management interface at `/admin/`.

## Tech Stack

- Backend: Django 6.1, SQLite
- Frontend: TailwindCSS 3 (CLI build), vanilla JS

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py migrate
./venv/bin/python manage.py seed_data   # optional demo data
./venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000

### Demo accounts (created by `seed_data`)

| Username | Password   | Role    |
|----------|------------|---------|
| admin    | admin123   | Manager |
| cashier  | cashier123 | Cashier |
| staff    | staff123   | Staff   |

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
