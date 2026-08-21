# AlvanzStock — File Map & Components Map

> How to navigate the codebase and find where each UI component is used.

## URL → View → Template map

| URL | View (file) | Template |
|---|---|---|
| `/` | `inventory/views.py` → `dashboard` | `templates/dashboard.html` |
| `/products/` | `inventory/views.py` → `product_list` | `inventory/product_list.html` |
| `/products/new/` | `inventory/views.py` → `product_create` | `inventory/product_form.html` |
| `/products/<id>/` | `inventory/views.py` → `product_detail` | `inventory/product_detail.html` |
| `/products/<id>/edit/` | `inventory/views.py` → `product_edit` | `inventory/product_form.html` |
| `/products/<id>/delete/` | `inventory/views.py` → `product_delete` | redirects |
| `/categories/` | `inventory/views.py` → `category_list` | `inventory/category_list.html` |
| `/categories/new/` | `inventory/views.py` → `category_create` | `inventory/category_form.html` |
| `/categories/<id>/delete/` | `inventory/views.py` → `category_delete` | redirects |
| `/stock/new/` | `inventory/views.py` → `stock_transaction_create` | `inventory/stock_form.html` |
| `/stock/` | `inventory/views.py` → `stock_transaction_list` | `inventory/stock_list.html` |
| `/low-stock/` | `inventory/views.py` → `low_stock` | `inventory/low_stock.html` |
| `/pos/` | `pos/views.py` → `pos_screen` | `pos/pos_screen.html` |
| `/pos/checkout/` | `pos/views.py` → `pos_checkout` (JSON API) | — |
| `/receipt/<id>/` | `pos/views.py` → `sale_receipt` | `pos/receipt.html` |
| `/sales/` | `pos/views.py` → `sales_list` | `pos/sales_list.html` |
| `/reports/sales/` | `pos/views.py` → `sales_report` | `reports/sales_report.html` |
| `/reports/inventory/` | `pos/views.py` → `inventory_report` | `reports/inventory_report.html` |
| `/accounts/login/` | `accounts/views.py` → `AlvanzLoginView` | `registration/login.html` |
| `/admin/` | Django admin | — |

Routing: `alvanzstock/urls.py` → `inventory/urls.py`, `pos/urls.py`, `accounts/urls.py`.

## Data models → app

| Model | File | Purpose |
|---|---|---|
| `User` (custom, has `role`) | `accounts/models.py` | Manager / Cashier / Staff |
| `Category` | `inventory/models.py` | Product grouping |
| `Product` (`quantity`, `min_stock_level`) | `inventory/models.py` | Stock + low-stock threshold |
| `StockTransaction` (IN / OUT / ADJ) | `inventory/models.py` | Moves stock, auto-updates `Product.quantity` |
| `Sale` | `pos/models.py` | Receipt, totals, change |
| `SaleItem` | `pos/models.py` | Line items |
| `record_sale()` | `pos/models.py` | Atomic checkout: creates Sale + items + stock-out txns |

## Components map

### Layout component

**`templates/base.html`** — everything extends it.
- Blocks: `title`, `content` (main), `bare` (login only), `scripts` (extra JS)
- Desktop sidebar (nav links to all modules) + mobile top nav
- Message banners (`{% if messages %}`), user role badge, logout

| Template | Extends `base.html` |
|---|---|
| all templates except `pos/receipt.html` | yes |
| `registration/login.html` | yes (uses `bare` block, no sidebar) |
| `pos/receipt.html` | no — standalone printable page |

### Reusable CSS components (defined in `static/css/input.css` → `@layer components`)

| Component | Usage |
|---|---|
| `.btn` | base button — do not use directly |
| `.btn-primary` | amber action button → *13 templates* (login, all forms, all list pages, POS, sales) |
| `.btn-secondary` | outlined neutral button → *10 templates* (filters, cancel, print, nav pills) |
| `.btn-danger` | red delete button → `product_detail.html` only |
| `.card` | white rounded panel → *13 templates* (dashboard cards, tables, forms, POS cart) |
| `.input` | form field styling → `product_form`, `category_form`, `stock_form`, `pos_screen`, `sales_list`, `login` |
| `.label` | form label → all form templates |
| `.table-head` | table `<th>` → 8 templates with tables |
| `.table-cell` | table `<td>` → same 8 templates as `.table-head` |

Tables use `.table-head` / `.table-cell` in: `dashboard`, `product_list`, `product_detail`, `stock_list`, `low_stock`, `sales_list`, `sales_report`, `inventory_report`.

### Inline page components (no include files)

| Component | Lives in | Used by |
|---|---|---|
| Stat card (icon + number) | `dashboard.html` | dashboard overview |
| Low-stock badge (red/green pill) | `product_list`, `product_detail`, `inventory_report` | stock status |
| POS cart + product grid | `pos/pos_screen.html` | POS screen |
| Receipt modal (iframe) | `pos/pos_screen.html` | shows `receipt.html` after checkout |
| Period filter pills | `reports/sales_report.html` | Today / Last 7 Days / This Month |

## Static assets

```
static/css/input.css    <- Tailwind source (@tailwind + component classes)
static/css/output.css   <- compiled CSS (Django serves this)
tailwind.config.js      <- scans ./templates/**/*.html
```

Edit templates → run `npm run build:css` to regenerate `output.css`.

## Utilities

| Command | File |
|---|---|
| `manage.py seed_data` | `inventory/management/commands/seed_data.py` |
| User / role admin | `accounts/admin.py` |
| Product / category / stock admin | `inventory/admin.py` |
| Sale admin | `pos/admin.py` |
