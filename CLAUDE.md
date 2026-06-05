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
| `cards_bp` | `/cards` | Credit/debit card management and invoices |
| `goals_bp` | `/goals` | Financial goals and progress tracking |

**Models** ([app/models.py](app/models.py)):
- `User` — hardcoded to Tiago/Greyce (seeded in `_seed_users`)
- `Expense` — single expense or one installment of a group; stores `year`, `month`, `day` as separate integers; has `payment_method` (Cartão de Crédito, Cartão de Débito, PIX, VR, VA, Dinheiro) and `bank` (links to a card label)
- `InstallmentGroup` — parent record for parcelado (credit card installment) purchases; deleting a group cascades to all its `Expense` rows
- `Salary` — one record per user/year/month combination (unique constraint); upserted on the manage page
- `CreditCard` — a card registered by the user; has `label`, `card_type` ('vr', 'va', 'credit', 'debit'), `supports_credit` (bool), `supports_debit` (bool), `limit` and `vr_monthly_limit` fields
- `CreditAccount` — monthly VR/VA balance record per card/year/month; tracks `carry_over` from previous months
- `Goal` — financial goal with `type` ('saving', 'spending_limit', 'debt_reduction'), `target_amount`, `start_date`, `due_date`, `category`, `completed_at`

**Installment logic** ([app/routes/expenses.py](app/routes/expenses.py) `_create_installments`): when payment method is "Cartão de Crédito" and type is "parcelado", a single purchase is split across N consecutive months. The last installment absorbs any rounding remainder.

**Card service** ([app/services/card_service.py](app/services/card_service.py)):
- `get_invoice(card, month, year)` — returns both `expenses` (credit) and `debit_expenses` separately, along with totals, by-day breakdown, category totals, and chart data for each side
- `vr_va_balance(card, month, year)` — calculates VR/VA available balance including `carry_over` from previous months (remaining balance carries forward automatically)
- Mixed cards (`supports_credit=True` and `supports_debit=True`) show separate sections in the invoice

**Chart API** ([app/routes/api.py](app/routes/api.py)): five endpoints feed the dashboard charts. All accept `?month=&year=` query params (default: current month). The `/payment-methods` and `/monthly-vs-salary` endpoints always return the last 6 months.

**Services:**
- [app/services/insight_service.py](app/services/insight_service.py) — generates insight dicts with `type`, `icon`, `title`, `message`, `value`, and `link` fields; `link` enables clickable insights that navigate to filtered expense/card pages
- [app/services/goal_service.py](app/services/goal_service.py) — calculates goal progress (`calculate`, `calculate_all`), generates coaching messages, and produces insights/alerts for the dashboard
- [app/services/alert_service.py](app/services/alert_service.py) — aggregates alerts from goals and other sources

**Jinja2 filters** (registered in `create_app`):
- `|brl` — formats a number as `R$ 1.234,56`
- `|mes_nome` — converts a month integer to a 3-letter Portuguese abbreviation

**Frontend**: plain Bootstrap 5 + vanilla JS.
- [app/static/js/expense_form.js](app/static/js/expense_form.js) — controls dynamic show/hide of bank, installment, and billing hint fields; billing hint is suppressed for non-credit payment methods
- [app/static/js/charts/dashboard.js](app/static/js/charts/dashboard.js) — fetches API endpoints and renders Chart.js charts; "Formas de Pagamento" is a doughnut chart aggregating totals per payment method
- [app/static/js/charts.js](app/static/js/charts.js) — legacy chart entry point

**Insights panel** ([app/templates/components/insights_panel.html](app/templates/components/insights_panel.html)): insight items render as `<a>` tags when `ins.link` is present (clickable, with chevron arrow hover effect) or `<div>` when no link. Hover styles per alert type are in [app/static/css/style.css](app/static/css/style.css).

## GitHub

Repositório: **https://github.com/tpaixao13/controledegastos**

O arquivo [.claude/settings.json](.claude/settings.json) configura um hook `PostToolUse` que faz commit e push automaticamente para o GitHub sempre que Claude editar ou criar um arquivo. O commit usa a mensagem `auto(<tool>): <arquivo>`.

Para o hook funcionar, o `gh` CLI deve estar autenticado:
```bash
"C:\Program Files\GitHub CLI\gh.exe" auth status
```

Se não estiver autenticado:
```bash
"C:\Program Files\GitHub CLI\gh.exe" auth login
```
