# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Activate virtualenv (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server (port 5000)
python run.py
```

The app auto-creates the SQLite database (`instance/gastos.db`) and seeds two hardcoded users (`Tiago` and `Greyce`) on first run.

## Environment

Copy `.env` and set `SECRET_KEY` for production. In development the app uses a fallback key and SQLite. Production can override `DATABASE_URL` via environment variable (see [config.py](config.py)).

## Architecture

Flask app using the application factory pattern (`create_app` in [app/__init__.py](app/__init__.py)).

**Blueprints:**

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `main_bp` | `/` | Dashboard – monthly summary per user |
| `expenses_bp` | `/expenses` | CRUD for expenses |
| `salaries_bp` | `/salaries` | Register/update monthly salaries |
| `api_bp` | `/api/chart` | JSON endpoints consumed by Chart.js |

**Models** ([app/models.py](app/models.py)):
- `User` — hardcoded to Tiago/Greyce (seeded in `_seed_users`)
- `Expense` — single expense or one installment of a group; stores `year`, `month`, `day` as separate integers
- `InstallmentGroup` — parent record for parcelado (credit card installment) purchases; deleting a group cascades to all its `Expense` rows
- `Salary` — one record per user/year/month combination (unique constraint); upserted on the manage page

**Installment logic** ([app/routes/expenses.py:138](app/routes/expenses.py#L138) `_create_installments`): when payment method is "Cartão de Crédito" and type is "parcelado", a single purchase is split across N consecutive months. The last installment absorbs any rounding remainder.

**Chart API** ([app/routes/api.py](app/routes/api.py)): five endpoints feed the dashboard charts. All accept `?month=&year=` query params (default: current month). The `/payment-methods` and `/monthly-vs-salary` endpoints always return the last 6 months.

**Jinja2 filters** (registered in `create_app`):
- `|brl` — formats a number as `R$ 1.234,56`
- `|mes_nome` — converts a month integer to a 3-letter Portuguese abbreviation

**Frontend**: plain Bootstrap 5 + vanilla JS. [app/static/js/expense_form.js](app/static/js/expense_form.js) controls the dynamic show/hide of bank and installment fields. [app/static/js/charts.js](app/static/js/charts.js) fetches the API endpoints and renders Chart.js charts on the dashboard.
