import json
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import CreditCard, Expense
from app.forms import CreditCardForm
from app.utils import tenant_user_ids, tenant_users, month_offset
from datetime import datetime

cards_bp = Blueprint('cards', __name__, url_prefix='/cards')

MONTH_NAMES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
               'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

MONTH_NAMES_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                     'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

# Paleta de cores para os cartões no gráfico
_CHART_COLORS = [
    'rgba(13,110,253,0.8)',
    'rgba(220,53,69,0.8)',
    'rgba(25,135,84,0.8)',
    'rgba(255,193,7,0.8)',
    'rgba(13,202,240,0.8)',
    'rgba(111,66,193,0.8)',
]


def _billing_month(purchase_day: int, purchase_month: int, purchase_year: int,
                   best_buy_day: int) -> tuple[int, int]:
    if purchase_day <= best_buy_day:
        return purchase_month, purchase_year
    return month_offset(purchase_month, purchase_year, 1)


def _chart_data(cards, invoice_month, invoice_year):
    """Retorna dados dos últimos 6 meses por cartão para o gráfico."""
    months = [month_offset(invoice_month, invoice_year, -i) for i in range(5, -1, -1)]
    labels = [f'{MONTH_NAMES_SHORT[m - 1]}/{y}' for m, y in months]

    datasets = []
    for i, card in enumerate(cards):
        totals = []
        for m, y in months:
            total = db.session.query(
                db.func.coalesce(db.func.sum(Expense.amount), 0)
            ).filter(
                Expense.card_id == card.id,
                Expense.month == m,
                Expense.year == y,
            ).scalar()
            totals.append(float(total))

        datasets.append({
            'label': card.label,
            'data': totals,
            'backgroundColor': _CHART_COLORS[i % len(_CHART_COLORS)],
            'borderRadius': 4,
        })

    return {'labels': labels, 'datasets': datasets}


@cards_bp.route('/')
def index():
    uids = tenant_user_ids()
    cards = (CreditCard.query
             .filter(CreditCard.user_id.in_(uids))
             .order_by(CreditCard.bank, CreditCard.last_digits)
             .all())

    now = datetime.now()
    form = CreditCardForm()

    invoice_month = request.args.get('month', now.month, type=int)
    invoice_year = request.args.get('year', now.year, type=int)

    card_invoices = {}
    for card in cards:
        expenses = (Expense.query
                    .filter(Expense.card_id == card.id,
                            Expense.month == invoice_month,
                            Expense.year == invoice_year)
                    .order_by(Expense.day)
                    .all())
        total = sum(float(e.amount) for e in expenses)
        card_invoices[card.id] = {'expenses': expenses, 'total': total}

    prev_month, prev_year = month_offset(invoice_month, invoice_year, -1)
    next_month, next_year = month_offset(invoice_month, invoice_year, 1)

    chart_json = json.dumps(_chart_data(cards, invoice_month, invoice_year)) if cards else None

    return render_template('cards/index.html',
                           cards=cards,
                           form=form,
                           card_invoices=card_invoices,
                           invoice_month=invoice_month,
                           invoice_year=invoice_year,
                           month_name=MONTH_NAMES[invoice_month - 1],
                           prev_month=prev_month, prev_year=prev_year,
                           next_month=next_month, next_year=next_year,
                           chart_json=chart_json)


@cards_bp.route('/add', methods=['POST'])
def add():
    uids = tenant_user_ids()
    form = CreditCardForm()
    if form.validate_on_submit():
        user_id = request.form.get('user_id', type=int)
        if not user_id or user_id not in uids:
            user_id = uids[0] if uids else None

        if form.best_buy_day.data >= form.due_day.data:
            flash('O melhor dia de compra deve ser anterior ao dia de vencimento.', 'warning')
            return redirect(url_for('cards.index'))

        card = CreditCard(
            user_id=user_id,
            nickname=form.nickname.data or None,
            last_digits=form.last_digits.data,
            bank=form.bank.data or None,
            due_day=form.due_day.data,
            best_buy_day=form.best_buy_day.data,
        )
        db.session.add(card)
        db.session.commit()
        flash(f'Cartão •••• {card.last_digits} adicionado com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')
    return redirect(url_for('cards.index'))


@cards_bp.route('/edit/<int:card_id>', methods=['POST'])
def edit(card_id):
    uids = tenant_user_ids()
    card = CreditCard.query.filter(CreditCard.id == card_id,
                                   CreditCard.user_id.in_(uids)).first_or_404()
    form = CreditCardForm()
    if form.validate_on_submit():
        if form.best_buy_day.data >= form.due_day.data:
            flash('O melhor dia de compra deve ser anterior ao dia de vencimento.', 'warning')
            return redirect(url_for('cards.index'))

        card.nickname = form.nickname.data or None
        card.last_digits = form.last_digits.data
        card.bank = form.bank.data or None
        card.due_day = form.due_day.data
        card.best_buy_day = form.best_buy_day.data
        db.session.commit()
        flash('Cartão atualizado com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')
    return redirect(url_for('cards.index'))


@cards_bp.route('/delete/<int:card_id>', methods=['POST'])
def delete(card_id):
    uids = tenant_user_ids()
    card = CreditCard.query.filter(CreditCard.id == card_id,
                                   CreditCard.user_id.in_(uids)).first_or_404()
    # Desvincula despesas antes de excluir
    Expense.query.filter_by(card_id=card.id).update({'card_id': None})
    db.session.delete(card)
    db.session.commit()
    flash('Cartão excluído. As despesas vinculadas foram mantidas sem vínculo.', 'warning')
    return redirect(url_for('cards.index'))


@cards_bp.route('/api/info/<int:card_id>')
def api_card_info(card_id):
    """Retorna JSON com info do cartão para o formulário de despesas."""
    from flask import jsonify
    uids = tenant_user_ids()
    card = CreditCard.query.filter(CreditCard.id == card_id,
                                   CreditCard.user_id.in_(uids)).first_or_404()
    return jsonify({
        'id': card.id,
        'bank': card.bank or '',
        'last_digits': card.last_digits,
        'due_day': card.due_day,
        'best_buy_day': card.best_buy_day,
        'label': card.label,
    })
