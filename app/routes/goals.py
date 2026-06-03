from datetime import date as _date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from app import db
from app.models import Goal, User
from app.utils import tenant_user_ids, tenant_users, get_month_year
from app.services.goal_service import calculate_all
from app.forms import CATEGORIES

goals_bp = Blueprint('goals', __name__, url_prefix='/goals')

MONTH_NAMES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
               'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']


def _tenant_goals(uids):
    return Goal.query.filter(Goal.user_id.in_(uids), Goal.active == True).order_by(Goal.created_at).all()


@goals_bp.route('/')
def index():
    uids  = tenant_user_ids()
    users = tenant_users().order_by(User.name).all()
    goals = _tenant_goals(uids)
    month, year = get_month_year()

    goals_data = calculate_all(goals, uids, month, year)

    return render_template('goals/index.html',
                           goals_data=goals_data,
                           users=users,
                           categories=sorted(CATEGORIES),
                           month=month, year=year,
                           month_name=MONTH_NAMES[month - 1])


@goals_bp.route('/add', methods=['POST'])
def add():
    uids  = tenant_user_ids()
    user_id = request.form.get('user_id', type=int)
    if not user_id or user_id not in uids:
        user_id = uids[0] if uids else None
    if not user_id:
        flash('Usuário inválido.', 'danger')
        return redirect(url_for('goals.index'))

    gtype         = request.form.get('type', '').strip()
    title         = request.form.get('title', '').strip()
    target_raw    = request.form.get('target_amount', '').replace(',', '.')
    category      = request.form.get('category', '').strip() or None
    due_date_raw  = request.form.get('due_date', '').strip()
    start_date_raw= request.form.get('start_date', '').strip()

    if not title or not gtype or not target_raw:
        flash('Preencha título, tipo e valor.', 'danger')
        return redirect(url_for('goals.index'))

    try:
        target = float(target_raw)
        if target <= 0:
            raise ValueError
    except ValueError:
        flash('Valor inválido.', 'danger')
        return redirect(url_for('goals.index'))

    try:
        start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date() if start_date_raw else _date.today()
    except ValueError:
        start_date = _date.today()

    try:
        due_date = datetime.strptime(due_date_raw, '%Y-%m-%d').date() if due_date_raw else None
    except ValueError:
        due_date = None

    goal = Goal(
        user_id=user_id,
        title=title,
        type=gtype,
        target_amount=target,
        category=category,
        due_date=due_date,
        start_date=start_date,
    )
    db.session.add(goal)
    db.session.commit()
    flash(f'Meta "{title}" criada com sucesso!', 'success')
    return redirect(url_for('goals.index'))


@goals_bp.route('/edit/<int:goal_id>', methods=['POST'])
def edit(goal_id):
    uids = tenant_user_ids()
    goal = Goal.query.filter(Goal.id == goal_id, Goal.user_id.in_(uids)).first_or_404()

    goal.title        = request.form.get('title', goal.title).strip()
    goal.type         = request.form.get('type', goal.type).strip()
    goal.category     = request.form.get('category', '').strip() or None
    target_raw = request.form.get('target_amount', '').replace(',', '.')
    try:
        goal.target_amount = float(target_raw) if target_raw else goal.target_amount
    except ValueError:
        pass

    due_raw = request.form.get('due_date', '').strip()
    try:
        goal.due_date = datetime.strptime(due_raw, '%Y-%m-%d').date() if due_raw else None
    except ValueError:
        pass

    db.session.commit()
    flash('Meta atualizada com sucesso!', 'success')
    return redirect(url_for('goals.index'))


@goals_bp.route('/complete/<int:goal_id>', methods=['POST'])
def complete(goal_id):
    uids = tenant_user_ids()
    goal = Goal.query.filter(Goal.id == goal_id, Goal.user_id.in_(uids)).first_or_404()
    goal.completed_at = datetime.utcnow()
    db.session.commit()
    flash(f'🎉 Meta "{goal.title}" marcada como concluída!', 'success')
    return redirect(url_for('goals.index'))


@goals_bp.route('/delete/<int:goal_id>', methods=['POST'])
def delete(goal_id):
    uids = tenant_user_ids()
    goal = Goal.query.filter(Goal.id == goal_id, Goal.user_id.in_(uids)).first_or_404()
    goal.active = False
    db.session.commit()
    flash(f'Meta "{goal.title}" arquivada.', 'warning')
    return redirect(url_for('goals.index'))
