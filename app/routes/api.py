import calendar
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app import db
from app.models import Expense, Salary, User, Investment
from app.utils import tenant_user_ids, tenant_users, MONTH_NAMES_SHORT, _fetch_json, get_selic_rate, month_offset

api_bp = Blueprint('api', __name__, url_prefix='/api/chart')

CATEGORY_COLORS = {
    'Alimentação': '#FF6384',
    'Beleza': '#f72585',
    'Educação': '#FFCE56',
    'Lazer': '#FF9F40',
    'Moradia': '#9966FF',
    'Saúde': '#4BC0C0',
    'Internet': '#4361ee',
    'Telefone': '#43aa8b',
    'Transporte': '#36A2EB',
    'Outros': '#C9CBCF',
}

PAYMENT_COLORS = {
    'PIX': '#32bcad',
    'Cartão de Débito': '#0d6efd',
    'Cartão de Crédito': '#6f42c1',
    'Dinheiro': '#198754',
}

MONTH_NAMES = MONTH_NAMES_SHORT


def _get_month_year():
    now = datetime.now()
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)
    if not 1 <= month <= 12:
        month = now.month
    if not 2000 <= year <= 2100:
        year = now.year
    return month, year


def _last_n_months(n=6, end_month=None, end_year=None):
    now = datetime.now()
    em = end_month or now.month
    ey = end_year or now.year
    return [month_offset(em, ey, -i) for i in range(n - 1, -1, -1)]


@api_bp.route('/doughnut')
def doughnut():
    month, year = _get_month_year()
    uids = tenant_user_ids()
    rows = (db.session.query(Expense.category, func.sum(Expense.amount))
            .filter(Expense.user_id.in_(uids), Expense.year == year, Expense.month == month)
            .group_by(Expense.category)
            .all())

    labels = [r[0] for r in rows]
    data = [float(r[1]) for r in rows]
    colors = [CATEGORY_COLORS.get(lbl, '#C9CBCF') for lbl in labels]

    total_salary = (db.session.query(func.sum(Salary.amount))
                    .filter(Salary.user_id.in_(uids), Salary.year == year, Salary.month == month)
                    .scalar() or 0)

    return jsonify({'labels': labels, 'data': data, 'colors': colors, 'total_salary': float(total_salary)})


@api_bp.route('/monthly-vs-salary')
def monthly_vs_salary():
    n = request.args.get('months', 6, type=int)
    n = max(1, min(n, 24))
    end_month, end_year = _get_month_year()
    months = _last_n_months(n, end_month, end_year)
    labels = [f'{MONTH_NAMES[m-1]}/{y}' for m, y in months]
    uids = tenant_user_ids()
    gastos = []
    salarios = []

    for m, y in months:
        total = (db.session.query(func.sum(Expense.amount))
                 .filter(Expense.user_id.in_(uids), Expense.year == y, Expense.month == m).scalar() or 0)
        sal = (db.session.query(func.sum(Salary.amount))
               .filter(Salary.user_id.in_(uids), Salary.year == y, Salary.month == m).scalar() or 0)
        gastos.append(float(total))
        salarios.append(float(sal))

    return jsonify({'labels': labels, 'gastos': gastos, 'salarios': salarios})


@api_bp.route('/user-comparison')
def user_comparison():
    month, year = _get_month_year()
    users = tenant_users().order_by(User.name).all()
    labels = [u.name for u in users]
    gastos = []
    salarios = []

    for u in users:
        total = (db.session.query(func.sum(Expense.amount))
                 .filter_by(user_id=u.id, year=year, month=month).scalar() or 0)
        sal = (db.session.query(func.sum(Salary.amount))
               .filter_by(user_id=u.id, year=year, month=month).scalar() or 0)
        gastos.append(float(total))
        salarios.append(float(sal))

    return jsonify({'labels': labels, 'gastos': gastos, 'salarios': salarios})


@api_bp.route('/daily')
def daily():
    month, year = _get_month_year()
    _, days_in_month = calendar.monthrange(year, month)
    uids = tenant_user_ids()

    rows = (db.session.query(Expense.day, func.sum(Expense.amount))
            .filter(Expense.user_id.in_(uids), Expense.year == year, Expense.month == month)
            .group_by(Expense.day)
            .all())

    daily_map = {r[0]: float(r[1]) for r in rows}
    labels = list(range(1, days_in_month + 1))
    data = []
    cumulative = 0
    for d in labels:
        cumulative += daily_map.get(d, 0)
        data.append(round(cumulative, 2))

    return jsonify({'labels': labels, 'data': data})


@api_bp.route('/payment-methods')
def payment_methods():
    n = request.args.get('months', 6, type=int)
    n = max(1, min(n, 24))
    end_month, end_year = _get_month_year()
    months = _last_n_months(n, end_month, end_year)
    labels = [f'{MONTH_NAMES[m-1]}/{y}' for m, y in months]
    methods = list(PAYMENT_COLORS.keys())
    uids = tenant_user_ids()
    datasets = []

    for method in methods:
        values = []
        for m, y in months:
            total = (db.session.query(func.sum(Expense.amount))
                     .filter(Expense.user_id.in_(uids), Expense.year == y,
                             Expense.month == m, Expense.payment_method == method)
                     .scalar() or 0)
            values.append(float(total))
        datasets.append({
            'label': method,
            'data': values,
            'backgroundColor': PAYMENT_COLORS[method],
        })

    return jsonify({'labels': labels, 'datasets': datasets})


@api_bp.route('/pending-vs-paid')
def pending_vs_paid():
    month, year = _get_month_year()
    uids = tenant_user_ids()
    paid_total = (db.session.query(func.sum(Expense.amount))
                  .filter(Expense.user_id.in_(uids), Expense.year == year,
                          Expense.month == month, Expense.paid == True).scalar() or 0)
    pending_total = (db.session.query(func.sum(Expense.amount))
                     .filter(Expense.user_id.in_(uids), Expense.year == year,
                             Expense.month == month, Expense.paid.isnot(True)).scalar() or 0)
    return jsonify({
        'labels': ['Pago', 'Pendente'],
        'data': [float(paid_total), float(pending_total)],
        'colors': ['#198754', '#ffc107'],
    })


@api_bp.route('/cdi-rate')
def cdi_rate():
    """Retorna taxa Selic atual do BCB e sugestões por tipo de investimento."""
    data = _fetch_json(
        'https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json',
        'selic'
    )
    selic = 14.75  # fallback
    if data and len(data) > 0:
        try:
            selic = float(data[0]['valor'].replace(',', '.'))
        except Exception:
            pass

    suggestions = {
        'Tesouro Selic': round(selic, 2),
        'CDB': round(selic, 2),
        'LCI': round(selic * 0.87, 2),
        'LCA': round(selic * 0.87, 2),
        'CRI/CRA': round(selic * 0.95, 2),
        'Debêntures': round(selic * 1.05, 2),
        'COE': round(selic * 0.90, 2),
        'Fundo de Renda Fixa': round(selic * 0.95, 2),
        'Fundo Multimercado': round(selic * 1.10, 2),
        'Tesouro IPCA+': round(selic * 0.60, 2),
        'Tesouro Prefixado': round(selic * 0.95, 2),
        'Poupança': round(selic * 0.70, 2),
        'Ações': 0,
        'FIIs': 0,
        'Criptomoedas': 0,
        'Outros': 0,
    }
    return jsonify({'selic': selic, 'suggestions': suggestions})


@api_bp.route('/crypto-price')
def crypto_price():
    """Retorna cotação atual de uma ou mais criptomoedas em BRL via CoinGecko."""
    coins = request.args.get('coins', 'bitcoin')
    data = _fetch_json(
        f'https://api.coingecko.com/api/v3/simple/price?ids={coins}&vs_currencies=brl&include_24hr_change=true',
        f'crypto_{coins}',
        ttl=300  # 5 minutos
    )
    if not data:
        return jsonify({'error': 'Não foi possível obter cotação'}), 503
    return jsonify(data)


@api_bp.route('/crypto-history')
def crypto_history():
    """Retorna histórico de preço de uma crypto em BRL (últimos 30 dias)."""
    coin = request.args.get('coin', 'bitcoin')
    days = request.args.get('days', 30, type=int)
    data = _fetch_json(
        f'https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=brl&days={days}',
        f'history_{coin}_{days}',
        ttl=3600
    )
    if not data or 'prices' not in data:
        return jsonify({'error': 'Indisponível'}), 503

    prices = data['prices']  # [[timestamp_ms, price], ...]
    labels = []
    values = []
    for ts, price in prices:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        labels.append(dt.strftime('%d/%m'))
        values.append(round(price, 2))

    return jsonify({'labels': labels, 'values': values})


@api_bp.route('/investments')
def investments_chart():
    """Retorna projeção de crescimento da carteira para os próximos 12 meses."""
    now = datetime.now()
    uids = tenant_user_ids()
    all_investments = Investment.query.filter(Investment.user_id.in_(uids)).all()

    if not all_investments:
        return jsonify({'labels': [], 'invested': [], 'projected': []})

    future_months = [month_offset(now.month, now.year, i) for i in range(12)]

    labels = [f'{MONTH_NAMES[m-1]}/{y}' for m, y in future_months]
    total_invested = sum(float(inv.amount) for inv in all_investments)
    invested_line = [round(total_invested, 2)] * 12

    projected = []
    for i, (fm, fy) in enumerate(future_months):
        total_value = 0.0
        for inv in all_investments:
            annual = float(inv.annual_rate) / 100.0
            monthly_rate = (1 + annual) ** (1 / 12) - 1
            # meses desde o investimento até este ponto
            months_elapsed = (fy - inv.year) * 12 + (fm - inv.month)
            if months_elapsed < 0:
                months_elapsed = 0
            value = float(inv.amount) * ((1 + monthly_rate) ** months_elapsed)
            total_value += value
        projected.append(round(total_value, 2))

    return jsonify({
        'labels': labels,
        'invested': invested_line,
        'projected': projected,
    })
