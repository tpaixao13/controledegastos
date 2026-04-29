from flask import Blueprint, render_template, request
from sqlalchemy import func
from app import db
from app.models import User, Expense, Salary
from app.utils import tenant_users, tenant_user_ids, MONTH_NAMES_FULL
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
    uids = tenant_user_ids()

    user_summaries = []
    total_salario = 0
    total_gasto = 0

    for u in users:
        salario = (db.session.query(func.sum(Salary.amount))
                   .filter_by(user_id=u.id, year=year, month=month).scalar() or 0)
        gasto = (db.session.query(func.sum(Expense.amount))
                 .filter_by(user_id=u.id, year=year, month=month).scalar() or 0)
        saldo = float(salario) - float(gasto)
        total_salario += float(salario)
        total_gasto += float(gasto)
        user_summaries.append({
            'user': u,
            'salario': float(salario),
            'gasto': float(gasto),
            'saldo': saldo,
        })

    saldo_combinado = total_salario - total_gasto

    recent = (Expense.query
              .filter(Expense.user_id.in_(uids))
              .filter_by(year=year, month=month)
              .order_by(Expense.day.desc(), Expense.created_at.desc())
              .limit(10).all())

    pending = (Expense.query
               .filter(Expense.user_id.in_(uids))
               .filter_by(year=year, month=month)
               .filter(Expense.paid.isnot(True))
               .order_by(Expense.day.asc(), Expense.created_at.asc())
               .all())
    total_pendente = sum(float(e.amount) for e in pending)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

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
