from flask import Blueprint, render_template, redirect, url_for, flash, request
from sqlalchemy import func
from app import db
from app.models import User, Salary
from app.forms import SalaryForm
from app.utils import tenant_users, tenant_user_ids
from datetime import datetime

salaries_bp = Blueprint('salaries', __name__, url_prefix='/salaries')


@salaries_bp.route('/', methods=['GET', 'POST'])
def manage():
    users = tenant_users().order_by(User.name).all()
    form = SalaryForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    now = datetime.now()
    if not form.is_submitted():
        form.year.data = now.year
        form.month.data = now.month

    if form.validate_on_submit():
        salary = Salary(
            user_id=form.user_id.data,
            year=form.year.data,
            month=form.month.data,
            amount=form.amount.data,
            company=form.company.data or None,
        )
        db.session.add(salary)
        db.session.commit()
        flash('Salário adicionado com sucesso!', 'success')
        return redirect(url_for('salaries.manage'))

    uids = [u.id for u in users]
    salaries = (Salary.query
                .filter(Salary.user_id.in_(uids))
                .join(User)
                .order_by(Salary.year.desc(), Salary.month.desc(), User.name)
                .all())

    # Agrupar por (ano, mês)
    from collections import defaultdict, OrderedDict
    groups = OrderedDict()
    for s in salaries:
        key = (s.year, s.month)
        if key not in groups:
            groups[key] = []
        groups[key].append(s)

    # Total combinado por (ano, mês)
    month_totals = {
        key: sum(float(s.amount) for s in items)
        for key, items in groups.items()
    }

    return render_template('salaries/manage.html',
                           form=form, groups=groups,
                           month_totals=month_totals, users=users)


@salaries_bp.route('/delete/<int:salary_id>', methods=['POST'])
def delete(salary_id):
    uids = tenant_user_ids()
    salary = Salary.query.filter(Salary.id == salary_id, Salary.user_id.in_(uids)).first_or_404()
    db.session.delete(salary)
    db.session.commit()
    flash('Salário removido.', 'info')
    return redirect(url_for('salaries.manage'))
