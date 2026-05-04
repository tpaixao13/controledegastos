from collections import OrderedDict
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import User, Salary
from app.forms import SalaryForm
from app.utils import tenant_users, tenant_user_ids, user_color_map
from datetime import datetime

salaries_bp = Blueprint('salaries', __name__, url_prefix='/salaries')

VARIABLE_SOURCES = [
    'Freelance', 'Dividendos', 'Aluguel', 'Bônus',
    'Comissão', 'Décimo Terceiro', 'PLR', 'Outros',
]


def _group_salaries(salaries, now):
    """Agrupa lista de Salary em OrderedDict (year,month) → [items], ordenado cronologicamente."""
    groups = OrderedDict()
    for s in salaries:
        key = (s.year, s.month)
        groups.setdefault(key, []).append(s)

    def _sort_key(ym):
        diff = (ym[0] - now.year) * 12 + (ym[1] - now.month)
        if diff == 0:
            return (0, 0)
        return (1, diff) if diff < 0 else (2, diff)

    return OrderedDict(sorted(groups.items(), key=lambda kv: _sort_key(kv[0])))


@salaries_bp.route('/', methods=['GET', 'POST'])
def manage():
    users = tenant_users().order_by(User.name).all()
    uids = [u.id for u in users]
    form = SalaryForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    now = datetime.now()
    if not form.is_submitted():
        form.year.data = now.year
        form.month.data = now.month

    active_tab = request.args.get('tab', 'fixa')

    if form.validate_on_submit():
        income_type = request.form.get('income_type', 'fixa')
        if income_type not in ('fixa', 'variavel'):
            income_type = 'fixa'
        salary = Salary(
            user_id=form.user_id.data,
            year=form.year.data,
            month=form.month.data,
            amount=form.amount.data,
            company=form.company.data or None,
            income_type=income_type,
        )
        db.session.add(salary)
        db.session.commit()
        flash('Renda adicionada com sucesso!', 'success')
        return redirect(url_for('salaries.manage', tab=income_type))

    all_salaries = (Salary.query
                    .filter(Salary.user_id.in_(uids))
                    .join(User)
                    .order_by(Salary.year.desc(), Salary.month.desc(), User.name)
                    .all())

    fixed = _group_salaries([s for s in all_salaries if s.income_type == 'fixa'], now)
    variable = _group_salaries([s for s in all_salaries if s.income_type == 'variavel'], now)

    def _totals(groups):
        return {key: sum(float(s.amount) for s in items) for key, items in groups.items()}

    return render_template('salaries/manage.html',
                           form=form,
                           fixed_groups=fixed,
                           variable_groups=variable,
                           fixed_totals=_totals(fixed),
                           variable_totals=_totals(variable),
                           variable_sources=VARIABLE_SOURCES,
                           active_tab=active_tab,
                           users=users,
                           user_colors=user_color_map(users))


@salaries_bp.route('/delete/<int:salary_id>', methods=['POST'])
def delete(salary_id):
    uids = tenant_user_ids()
    salary = Salary.query.filter(Salary.id == salary_id, Salary.user_id.in_(uids)).first_or_404()
    tab = request.form.get('tab', 'fixa')
    db.session.delete(salary)
    db.session.commit()
    flash('Renda removida.', 'info')
    return redirect(url_for('salaries.manage', tab=tab))
