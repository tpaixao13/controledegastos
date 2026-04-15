from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app import db
from app.models import Expense, Salary, User, Investment
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/chart')

CATEGORY_COLORS = {
    'Alimentação': '#FF6384',
    'Beleza': '#f72585',
    'Educação': '#FFCE56',
    'Lazer': '#FF9F40',
    'Moradia': '#9966FF',
    'Saúde': '#4BC0C0',
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


def _last_n_months(n=6):
    now = datetime.now()
    months = []
    for i in range(n - 1, -1, -1):
        m = (now.month - 1 - i) % 12 + 1
        y = now.year + ((now.month - 1 - i) // 12)
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

    return jsonify({'labels': labels, 'data': data, 'colors': colors})


@api_bp.route('/monthly-vs-salary')
def monthly_vs_salary():
    months = _last_n_months(6)
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
    months = _last_n_months(6)
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
