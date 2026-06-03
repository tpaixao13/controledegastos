from collections import OrderedDict
from flask import Blueprint, render_template, redirect, url_for, flash, request
from sqlalchemy import or_, and_
from app import db
from app.models import User, Salary, SalaryGroup
from app.forms import SalaryForm
from app.utils import tenant_users, tenant_user_ids, user_color_map, month_offset, MONTH_NAMES_SHORT
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


def _parse_payment_day(form):
    """Extracts and validates payment_day and payment_day_type from form."""
    pay_day_type = form.payment_day_type.data or None
    pay_day = form.payment_day.data if form.payment_day.data else None
    if not pay_day_type:
        pay_day = None
    elif pay_day_type == 'util' and pay_day and not 1 <= pay_day <= 22:
        return None, None, 'Dia útil deve ser entre 1 e 22.'
    elif pay_day_type == 'fixo' and pay_day and not 1 <= pay_day <= 31:
        return None, None, 'Dia fixo deve ser entre 1 e 31.'
    return pay_day_type, pay_day, None


@salaries_bp.route('/', methods=['GET', 'POST'])
def manage():
    users = tenant_users().order_by(User.name).all()
    uids = [u.id for u in users]
    form = SalaryForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    now = datetime.now()
    cur_month = request.args.get('month', now.month, type=int)
    cur_year  = request.args.get('year',  now.year,  type=int)

    if not form.is_submitted():
        form.year.data  = cur_year
        form.month.data = cur_month

    active_tab = request.args.get('tab', 'fixa')

    if form.validate_on_submit():
        income_type = request.form.get('income_type', 'fixa')
        if income_type not in ('fixa', 'variavel'):
            income_type = 'fixa'

        pay_day_type, pay_day, err = _parse_payment_day(form)
        if err:
            flash(err, 'danger')
            return redirect(url_for('salaries.manage', tab=income_type,
                                    month=cur_month, year=cur_year))

        if income_type == 'fixa' and form.is_recurring.data:
            n = form.recurring_months.data
            group = SalaryGroup(user_id=form.user_id.data)
            db.session.add(group)
            db.session.flush()

            for i in range(n):
                m, y = month_offset(form.month.data, form.year.data, i)
                db.session.add(Salary(
                    user_id=form.user_id.data,
                    year=y,
                    month=m,
                    amount=form.amount.data,
                    company=form.company.data or None,
                    income_type='fixa',
                    salary_group_id=group.id,
                    payment_day=pay_day,
                    payment_day_type=pay_day_type,
                    received=False,
                ))
            db.session.commit()
            m_fim, y_fim = month_offset(form.month.data, form.year.data, n - 1)
            flash(
                f'Renda fixa criada por {n} meses '
                f'({MONTH_NAMES_SHORT[form.month.data-1]}/{form.year.data}'
                f' → {MONTH_NAMES_SHORT[m_fim-1]}/{y_fim}).',
                'success'
            )
        else:
            db.session.add(Salary(
                user_id=form.user_id.data,
                year=form.year.data,
                month=form.month.data,
                amount=form.amount.data,
                company=form.company.data or None,
                income_type=income_type,
                payment_day=pay_day,
                payment_day_type=pay_day_type,
                received=False,
            ))
            db.session.commit()
            flash('Renda adicionada com sucesso!', 'success')

        return redirect(url_for('salaries.manage', tab=income_type,
                                month=cur_month, year=cur_year))

    all_salaries = (Salary.query
                    .filter(Salary.user_id.in_(uids),
                            Salary.year  == cur_year,
                            Salary.month == cur_month)
                    .join(User)
                    .order_by(User.name)
                    .all())

    fixed    = [s for s in all_salaries if s.income_type == 'fixa']
    variable = [s for s in all_salaries if s.income_type == 'variavel']

    return render_template('salaries/manage.html',
                           form=form,
                           fixed_items=fixed,
                           variable_items=variable,
                           fixed_total=sum(float(s.amount) for s in fixed),
                           variable_total=sum(float(s.amount) for s in variable),
                           variable_sources=VARIABLE_SOURCES,
                           active_tab=active_tab,
                           cur_month=cur_month,
                           cur_year=cur_year,
                           users=users,
                           user_colors=user_color_map(users))


@salaries_bp.route('/toggle-received/<int:salary_id>', methods=['POST'])
def toggle_received(salary_id):
    uids = tenant_user_ids()
    salary = Salary.query.filter(Salary.id == salary_id, Salary.user_id.in_(uids)).first_or_404()
    salary.received = not bool(salary.received)
    db.session.commit()
    tab   = request.form.get('tab', 'fixa')
    month = request.form.get('month', type=int) or datetime.now().month
    year  = request.form.get('year',  type=int) or datetime.now().year
    return redirect(url_for('salaries.manage', tab=tab, month=month, year=year))


@salaries_bp.route('/edit/<int:salary_id>', methods=['POST'])
def edit_salary(salary_id):
    uids = tenant_user_ids()
    salary = Salary.query.filter(Salary.id == salary_id, Salary.user_id.in_(uids)).first_or_404()

    try:
        amount = float(request.form.get('amount', '').replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        flash('Valor inválido.', 'danger')
        return redirect(url_for('salaries.manage', tab=salary.income_type))

    company = request.form.get('company') or None
    pay_day_type = request.form.get('payment_day_type') or None
    try:
        pay_day = int(request.form.get('payment_day', '') or '') if pay_day_type else None
    except ValueError:
        pay_day = None

    if pay_day_type == 'util' and pay_day and not 1 <= pay_day <= 22:
        flash('Dia útil deve ser entre 1 e 22.', 'danger')
        return redirect(url_for('salaries.manage', tab=salary.income_type))
    if pay_day_type == 'fixo' and pay_day and not 1 <= pay_day <= 31:
        flash('Dia fixo deve ser entre 1 e 31.', 'danger')
        return redirect(url_for('salaries.manage', tab=salary.income_type))
    if not pay_day_type:
        pay_day = None

    update_forward = request.form.get('update_forward') == '1'

    if update_forward and salary.salary_group_id:
        targets = Salary.query.filter(
            Salary.salary_group_id == salary.salary_group_id,
            Salary.user_id.in_(uids),
            or_(
                Salary.year > salary.year,
                and_(Salary.year == salary.year, Salary.month >= salary.month)
            )
        ).all()
        for s in targets:
            s.amount = amount
            s.company = company
            s.payment_day_type = pay_day_type
            s.payment_day = pay_day
    else:
        salary.amount = amount
        salary.company = company
        salary.payment_day_type = pay_day_type
        salary.payment_day = pay_day

    db.session.commit()
    flash('Renda atualizada com sucesso!', 'success')
    month = request.form.get('month', type=int) or salary.month
    year  = request.form.get('year',  type=int) or salary.year
    return redirect(url_for('salaries.manage', tab=salary.income_type, month=month, year=year))


@salaries_bp.route('/delete/<int:salary_id>', methods=['POST'])
def delete(salary_id):
    uids = tenant_user_ids()
    salary = Salary.query.filter(Salary.id == salary_id, Salary.user_id.in_(uids)).first_or_404()
    tab   = request.form.get('tab', 'fixa')
    month = request.form.get('month', type=int) or salary.month
    year  = request.form.get('year',  type=int) or salary.year
    db.session.delete(salary)
    db.session.commit()
    flash('Renda removida.', 'info')
    return redirect(url_for('salaries.manage', tab=tab, month=month, year=year))
