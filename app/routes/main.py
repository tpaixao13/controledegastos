from flask import Blueprint, render_template, request
from sqlalchemy import func
from app import db
from app.models import User, Expense, Salary, CreditCard, Goal
from app.utils import (tenant_users, tenant_user_ids, MONTH_NAMES_FULL,
                       month_offset, sum_expenses_month, sum_salaries_month,
                       user_color_map, get_month_year)
from app.services.insight_service import generate_insights
from app.services.goal_service import calculate_all as goals_calculate_all
from datetime import datetime

main_bp = Blueprint('main', __name__)


def _delta(cur: float, prev: float):
    """Variação percentual entre mês atual e anterior. None se prev == 0."""
    if prev == 0:
        return None
    return round((cur - prev) / prev * 100, 1)


@main_bp.route('/')
def index():
    now = datetime.now()
    month, year = get_month_year()

    users = tenant_users().order_by(User.name).all()
    uids = [u.id for u in users]

    prev_month, prev_year = month_offset(month, year, -1)
    next_month, next_year = month_offset(month, year,  1)

    # ── Totais do mês atual ──────────────────────────────────────
    expense_map = dict(
        db.session.query(Expense.user_id, func.sum(Expense.amount))
        .filter(Expense.user_id.in_(uids), Expense.year == year, Expense.month == month)
        .group_by(Expense.user_id).all()
    )
    salary_map = dict(
        db.session.query(Salary.user_id, func.sum(Salary.amount))
        .filter(Salary.user_id.in_(uids), Salary.year == year, Salary.month == month,
                Salary.received == True)
        .group_by(Salary.user_id).all()
    )

    user_summaries = []
    total_salario = total_gasto = 0.0
    for u in users:
        gasto   = float(expense_map.get(u.id) or 0)
        salario = float(salary_map.get(u.id) or 0)
        total_gasto   += gasto
        total_salario += salario
        user_summaries.append({'user': u, 'salario': salario, 'gasto': gasto, 'saldo': salario - gasto})

    saldo_combinado = total_salario - total_gasto

    # ── Cartão de Crédito — fatura do mês ───────────────────────
    credit_total = sum_expenses_month(uids, year, month,
                                      Expense.payment_method == 'Cartão de Crédito')

    # ── Mês anterior para deltas ─────────────────────────────────
    prev_gasto   = sum_expenses_month(uids, prev_year, prev_month)
    prev_salario = sum_salaries_month(uids, prev_year, prev_month)
    prev_credit  = sum_expenses_month(uids, prev_year, prev_month,
                                      Expense.payment_method == 'Cartão de Crédito')
    prev_saldo   = prev_salario - prev_gasto

    kpi_deltas = {
        'income':   _delta(total_salario, prev_salario),
        'expenses': _delta(total_gasto, prev_gasto),
        'credit':   _delta(credit_total, prev_credit),
        'balance':  _delta(saldo_combinado, prev_saldo),
    }

    # ── Insights financeiros ─────────────────────────────────────
    cards = CreditCard.query.filter(CreditCard.user_id.in_(uids)).all()
    insights = generate_insights(uids, month, year, cards=cards)

    # ── Despesas recentes e pendentes ────────────────────────────
    recent = (Expense.query
              .filter(Expense.user_id.in_(uids), Expense.year == year, Expense.month == month)
              .order_by(Expense.day.desc(), Expense.created_at.desc())
              .limit(10).all())

    pending = (Expense.query
               .filter(Expense.user_id.in_(uids),
                       Expense.year == year, Expense.month == month,
                       Expense.paid.isnot(True))
               .order_by(Expense.day.asc(), Expense.created_at.asc())
               .all())
    total_pendente = sum(float(e.amount) for e in pending)

    return render_template('index.html',
                           insights=insights,
                           today=now.date(),
                           user_summaries=user_summaries,
                           user_colors=user_color_map(users),
                           total_salario=total_salario,
                           total_gasto=total_gasto,
                           saldo_combinado=saldo_combinado,
                           credit_total=credit_total,
                           kpi_deltas=kpi_deltas,
                           recent=recent,
                           pending=pending,
                           total_pendente=total_pendente,
                           month=month,
                           year=year,
                           month_name=MONTH_NAMES_FULL[month - 1],
                           prev_month=prev_month, prev_year=prev_year,
                           next_month=next_month, next_year=next_year)
