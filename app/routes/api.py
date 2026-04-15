from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app import db
from app.models import Expense, Salary, User, Investment
from datetime import datetime
import urllib.request
import json
import time
import ssl

# Cache simples em memória
_cache = {}
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _fetch_json(url, cache_key, ttl=3600):
    """Busca JSON de URL externa com cache em memória."""
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]['ts'] < ttl:
        return _cache[cache_key]['data']
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ControleGastos/1.0)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        _cache[cache_key] = {'data': data, 'ts': now}
        return data
    except Exception as e:
        print(f'[_fetch_json] Erro ao buscar {url}: {e}')
        return None

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

MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def _get_month_year():
    now = datetime.now()
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)
    return month, year


def _last_n_months(n=6, end_month=None, end_year=None):
    now = datetime.now()
    em = end_month or now.month
    ey = end_year or now.year
    months = []
    for i in range(n - 1, -1, -1):
        m = (em - 1 - i) % 12 + 1
        y = ey + ((em - 1 - i) // 12)
        months.append((m, y))
    return months


@api_bp.route('/doughnut')
def doughnut():
    month, year = _get_month_year()
    rows = (db.session.query(Expense.category, func.sum(Expense.amount))
            .filter_by(year=year, month=month)
            .group_by(Expense.category)
            .all())

    labels = [r[0] for r in rows]
    data = [float(r[1]) for r in rows]
    colors = [CATEGORY_COLORS.get(lbl, '#C9CBCF') for lbl in labels]

    total_salary = db.session.query(func.sum(Salary.amount)).filter_by(year=year, month=month).scalar() or 0

    return jsonify({'labels': labels, 'data': data, 'colors': colors, 'total_salary': float(total_salary)})


@api_bp.route('/monthly-vs-salary')
def monthly_vs_salary():
    n = request.args.get('months', 6, type=int)
    n = max(1, min(n, 24))
    end_month, end_year = _get_month_year()
    months = _last_n_months(n, end_month, end_year)
    labels = [f'{MONTH_NAMES[m-1]}/{y}' for m, y in months]
    gastos = []
    salarios = []

    for m, y in months:
        total = db.session.query(func.sum(Expense.amount)).filter_by(year=y, month=m).scalar() or 0
        sal = db.session.query(func.sum(Salary.amount)).filter_by(year=y, month=m).scalar() or 0
        gastos.append(float(total))
        salarios.append(float(sal))

    return jsonify({'labels': labels, 'gastos': gastos, 'salarios': salarios})


@api_bp.route('/user-comparison')
def user_comparison():
    month, year = _get_month_year()
    users = User.query.order_by(User.name).all()
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
    import calendar
    _, days_in_month = calendar.monthrange(year, month)

    rows = (db.session.query(Expense.day, func.sum(Expense.amount))
            .filter_by(year=year, month=month)
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
    datasets = []

    for method in methods:
        values = []
        for m, y in months:
            total = (db.session.query(func.sum(Expense.amount))
                     .filter_by(year=y, month=m, payment_method=method).scalar() or 0)
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
    paid_total = (db.session.query(func.sum(Expense.amount))
                  .filter(Expense.year == year, Expense.month == month,
                          Expense.paid == True).scalar() or 0)
    pending_total = (db.session.query(func.sum(Expense.amount))
                     .filter(Expense.year == year, Expense.month == month,
                             Expense.paid.isnot(True)).scalar() or 0)
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
        from datetime import timezone
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        labels.append(dt.strftime('%d/%m'))
        values.append(round(price, 2))

    return jsonify({'labels': labels, 'values': values})


@api_bp.route('/investments')
def investments_chart():
    """Retorna projeção de crescimento da carteira para os próximos 12 meses."""
    now = datetime.now()
    all_investments = Investment.query.all()

    if not all_investments:
        return jsonify({'labels': [], 'invested': [], 'projected': []})

    # Gera os próximos 12 meses a partir do mês atual
    future_months = []
    for i in range(12):
        m = (now.month - 1 + i) % 12 + 1
        y = now.year + ((now.month - 1 + i) // 12)
        future_months.append((m, y))

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
