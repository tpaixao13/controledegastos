from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import User, Salary
from app.forms import SalaryForm
from datetime import datetime

salaries_bp = Blueprint('salaries', __name__, url_prefix='/salaries')


@salaries_bp.route('/', methods=['GET', 'POST'])
def manage():
    users = User.query.order_by(User.name).all()
    form = SalaryForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    now = datetime.now()
    form.year.data = form.year.data or now.year
    form.month.data = form.month.data or now.month

    if form.validate_on_submit():
        existing = Salary.query.filter_by(
            user_id=form.user_id.data,
            year=form.year.data,
            month=form.month.data
        ).first()

        if existing:
            existing.amount = form.amount.data
            flash('Salário atualizado com sucesso!', 'success')
        else:
            salary = Salary(
                user_id=form.user_id.data,
                year=form.year.data,
                month=form.month.data,
                amount=form.amount.data
            )
            db.session.add(salary)
            flash('Salário registado com sucesso!', 'success')

        db.session.commit()
        return redirect(url_for('salaries.manage'))

    # Buscar histórico de salários
    salaries = (Salary.query
                .join(User)
                .order_by(Salary.year.desc(), Salary.month.desc(), User.name)
                .all())

    return render_template('salaries/manage.html', form=form, salaries=salaries, users=users)
