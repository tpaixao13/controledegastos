from flask import Blueprint, render_template, request
from sqlalchemy import func
from app import db
from app.models import User, Expense, Salary
from app.utils import tenant_users, tenant_user_ids, MONTH_NAMES_FULL, month_offset, sum_expenses_month, sum_salaries_month
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    now = datetime.now()
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)
    if not 1 <= month <= 12:
        month = now.month
    if not 2000 <= year <= 2100:
        year = now.year

    users = tenant_users().order_by(User.name).all()
    uids = [u.id for u in users]

    # Duas queries GROUP BY em vez de 2×N queries individuais
    expense_map = dict(
        db.session.query(Expense.user_id, func.sum(Expense.amount))
        .filter(Expense.user_id.in_(uids), Expense.year == year, Expense.month == month)
        .group_by(Expense.user_id).all()
    )
    salary_map = dict(
        db.session.query(Salary.user_id, func.sum(Salary.amount))
        .filter(Salary.user_id.in_(uids), Salary.year == year, Salary.month == month)
        .group_by(Salary.user_id).all()
    )

    user_summaries = []
    total_salario = total_gasto = 0.0

    for u in users:
        gasto   = float(expense_map.get(u.id) or 0)
        salario = float(salary_map.get(u.id) or 0)
        total_gasto   += gasto
        total_salario += salario
        user_summaries.append({
            'user': u,
            'salario': salario,
            'gasto': gasto,
            'saldo': salario - gasto,
        })

    saldo_combinado = total_salario - total_gasto

    recent = (Expense.query
              .filter(Expense.user_id.in_(uids),
                      Expense.year == year, Expense.month == month)
              .order_by(Expense.day.desc(), Expense.created_at.desc())
              .limit(10).all())

    pending = (Expense.query
               .filter(Expense.user_id.in_(uids))
               .filter_by(year=year, month=month)
               .filter(Expense.paid.isnot(True))
               .order_by(Expense.day.asc(), Expense.created_at.asc())
               .all())
    total_pendente = sum(float(e.amount) for e in pending)

    prev_month, prev_year = month_offset(month, year, -1)
    next_month, next_year = month_offset(month, year,  1)

    return render_template('index.html',
                           today=now.date(),
                           user_summaries=user_summaries,
                           total_salario=total_salario,
                           total_gasto=total_gasto,
                           saldo_combinado=saldo_combinado,
                           recent=recent,
                           pending=pending,
                           total_pendente=total_pendente,
                           month=month,
                           year=year,
                           month_name=MONTH_NAMES_FULL[month - 1],
                           prev_month=prev_month,
                           prev_year=prev_year,
                           next_month=next_month,
                           next_year=next_year)
