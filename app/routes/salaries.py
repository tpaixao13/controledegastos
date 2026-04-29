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

    totals = (db.session.query(
                Salary.user_id, Salary.year, Salary.month,
                func.sum(Salary.amount).label('total'))
              .filter(Salary.user_id.in_(uids))
              .group_by(Salary.user_id, Salary.year, Salary.month)
              .all())
    totals_map = {(t.user_id, t.year, t.month): float(t.total) for t in totals}

    return render_template('salaries/manage.html',
                           form=form, salaries=salaries,
                           users=users, totals_map=totals_map)


@salaries_bp.route('/delete/<int:salary_id>', methods=['POST'])
def delete(salary_id):
    uids = tenant_user_ids()
    salary = Salary.query.filter(Salary.id == salary_id, Salary.user_id.in_(uids)).first_or_404()
    db.session.delete(salary)
    db.session.commit()
    flash('Salário removido.', 'info')
    return redirect(url_for('salaries.manage'))
