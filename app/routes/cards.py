import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from app import db
from app.models import CreditCard, CreditAccount, Expense
from app.forms import CreditCardForm
from app.utils import tenant_user_ids, tenant_users, month_offset
from app.services.card_service import (
    card_gradient, invoice_total, get_invoice, CATEGORY_ICONS,
    get_invoice_reference, get_invoice_label, vr_va_balance,
    credit_invoice_total, debit_total, account_credit_usage,
)
from datetime import datetime

cards_bp = Blueprint('cards', __name__, url_prefix='/cards')

MONTH_NAMES       = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                     'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
MONTH_NAMES_SHORT = ['Jan','Fev','Mar','Abr','Mai','Jun',
                     'Jul','Ago','Set','Out','Nov','Dez']

_CHART_COLORS = [
    'rgba(13,110,253,0.8)',   'rgba(220,53,69,0.8)',
    'rgba(25,135,84,0.8)',    'rgba(255,193,7,0.8)',
    'rgba(13,202,240,0.8)',   'rgba(111,66,193,0.8)',
]


def _get_or_create_account(user_id: int, bank: str | None,
                           credit_limit=None) -> 'CreditAccount | None':
    """
    Retorna a CreditAccount existente para (user_id, bank),
    ou cria uma nova se não existir. Retorna None se bank for vazio.
    """
    if not bank:
        return None
    account = CreditAccount.query.filter_by(user_id=user_id, bank=bank).first()
    if not account:
        account = CreditAccount(
            user_id=user_id,
            bank=bank,
            credit_limit=credit_limit or None,
        )
        db.session.add(account)
        db.session.flush()
    elif credit_limit and not account.credit_limit:
        account.credit_limit = credit_limit
    return account


def _history_chart(cards, invoice_month, invoice_year):
    """Gráfico de barras — últimos 6 meses por cartão."""
    months = [month_offset(invoice_month, invoice_year, -i) for i in range(5, -1, -1)]
    labels = [f'{MONTH_NAMES_SHORT[m-1]}/{y}' for m, y in months]
    datasets = []
    for i, card in enumerate(cards):
        totals = [invoice_total(card.id, m, y) for m, y in months]
        datasets.append({
            'label':           card.label,
            'data':            totals,
            'backgroundColor': _CHART_COLORS[i % len(_CHART_COLORS)],
            'borderRadius':    4,
        })
    return {'labels': labels, 'datasets': datasets}


# ── Index: lista de cartões ─────────────────────────────────────────

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
    invoice_year  = request.args.get('year',  now.year,  type=int)

    # Dados de cada cartão para exibição no widget
    card_data = []
    for card in cards:
        sc = bool(card.supports_credit)
        sd = bool(card.supports_debit)

        # Uso de crédito: nível de CONTA (todos os cartões do mesmo grupo)
        if sc and card.account_id:
            cr_total = account_credit_usage(card.account_id, invoice_month, invoice_year)
        elif sc:
            cr_total = credit_invoice_total(card.id, invoice_month, invoice_year)
        else:
            cr_total = 0.0

        db_total = debit_total(card.id, invoice_month, invoice_year) if sd else 0.0
        total    = cr_total if sc else (db_total if sd else
                   invoice_total(card.id, invoice_month, invoice_year))

        gradient, text_color = card_gradient(card)
        limit = card.effective_limit
        pct   = round(cr_total / limit * 100, 1) if (limit and sc) else None
        vr_bal = vr_va_balance(card, invoice_month, invoice_year)

        # Quantos cartões compartilham o limite
        account_cards = card.account.cards.count() if card.account_id else 1

        card_data.append({
            'card':          card,
            'total':         total,
            'credit_total':  cr_total,
            'debit_total':   db_total,
            'gradient':      gradient,
            'text_color':    text_color,
            'limit':         limit,
            'pct':           pct,
            'vr_balance':    vr_bal,
            'account_cards': account_cards,
        })

    prev_month, prev_year = month_offset(invoice_month, invoice_year, -1)
    next_month, next_year = month_offset(invoice_month, invoice_year,  1)

    history_chart = json.dumps(_history_chart(cards, invoice_month, invoice_year)) if cards else None

    return render_template('cards/index.html',
                           card_data=card_data,
                           form=form,
                           invoice_month=invoice_month,
                           invoice_year=invoice_year,
                           month_name=MONTH_NAMES[invoice_month - 1],
                           prev_month=prev_month, prev_year=prev_year,
                           next_month=next_month, next_year=next_year,
                           history_chart=history_chart)


# ── Invoice: fatura de um cartão ────────────────────────────────────

@cards_bp.route('/<int:card_id>/invoice')
def invoice(card_id):
    uids = tenant_user_ids()
    card = CreditCard.query.filter(CreditCard.id == card_id,
                                   CreditCard.user_id.in_(uids)).first_or_404()

    now = datetime.now()
    month = request.args.get('month', now.month, type=int)
    year  = request.args.get('year',  now.year,  type=int)

    inv = get_invoice(card, month, year)
    gradient, text_color = card_gradient(card)

    return render_template('cards/invoice.html',
                           card=card,
                           inv=inv,
                           month=month,
                           year=year,
                           month_name=MONTH_NAMES[month - 1],
                           gradient=gradient,
                           text_color=text_color,
                           category_icons=CATEGORY_ICONS,
                           chart_json=json.dumps(inv['chart']) if inv['chart'] else None)


# ── CRUD de cartões ─────────────────────────────────────────────────

@cards_bp.route('/add', methods=['POST'])
def add():
    uids = tenant_user_ids()
    form = CreditCardForm()
    if form.validate_on_submit():
        user_id = request.form.get('user_id', type=int)
        if not user_id or user_id not in uids:
            user_id = uids[0] if uids else None

        if (form.card_type.data or 'credit') == 'credit' and (form.best_buy_day.data or 0) >= (form.due_day.data or 31):
            flash('O melhor dia de compra deve ser anterior ao dia de vencimento.', 'warning')
            return redirect(url_for('cards.index'))

        st   = form.special_type.data or ''
        sc   = bool(form.supports_credit.data) if st not in ('vr', 'va') else False
        sd   = bool(form.supports_debit.data)  if st not in ('vr', 'va') else False
        ct   = st if st in ('vr', 'va') else ('credit' if sc else 'debit')
        bank = form.bank.data or None
        due  = form.due_day.data or 1
        best = form.best_buy_day.data or 1
        lim  = form.credit_limit.data or None

        # Auto-criar ou reusar conta de crédito por banco
        account = _get_or_create_account(user_id, bank, lim) if sc else None

        card = CreditCard(
            user_id=user_id,
            nickname=form.nickname.data or None,
            last_digits=form.last_digits.data,
            bank=bank,
            due_day=due,
            best_buy_day=best,
            credit_limit=lim,
            card_type=ct,
            supports_credit=sc,
            supports_debit=sd,
            is_virtual=bool(form.is_virtual.data),
            is_additional=bool(form.is_additional.data),
            monthly_amount=form.monthly_amount.data if st in ('vr', 'va') else None,
            renewal_day=form.renewal_day.data if st in ('vr', 'va') else None,
            account_id=account.id if account else None,
        )
        db.session.add(card)
        db.session.commit()
        flash(f'Cartão •••• {card.last_digits} adicionado com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
    return redirect(url_for('cards.index'))


@cards_bp.route('/edit/<int:card_id>', methods=['POST'])
def edit(card_id):
    uids = tenant_user_ids()
    card = CreditCard.query.filter(CreditCard.id == card_id,
                                   CreditCard.user_id.in_(uids)).first_or_404()
    form = CreditCardForm()
    if form.validate_on_submit():
        if (form.card_type.data or 'credit') == 'credit' and (form.best_buy_day.data or 0) >= (form.due_day.data or 31):
            flash('O melhor dia de compra deve ser anterior ao dia de vencimento.', 'warning')
            return redirect(url_for('cards.index'))

        st   = form.special_type.data or ''
        sc   = bool(form.supports_credit.data) if st not in ('vr', 'va') else False
        sd   = bool(form.supports_debit.data)  if st not in ('vr', 'va') else False
        ct   = st if st in ('vr', 'va') else ('credit' if sc else 'debit')
        bank = form.bank.data or None
        lim  = form.credit_limit.data or None

        card.nickname        = form.nickname.data or None
        card.last_digits     = form.last_digits.data
        card.bank            = bank
        card.due_day         = form.due_day.data or 1
        card.best_buy_day    = form.best_buy_day.data or 1
        card.credit_limit    = lim
        card.card_type       = ct
        card.supports_credit = sc
        card.supports_debit  = sd
        card.is_virtual      = bool(form.is_virtual.data)
        card.is_additional   = bool(form.is_additional.data)
        card.monthly_amount  = form.monthly_amount.data if st in ('vr', 'va') else None
        card.renewal_day     = form.renewal_day.data if st in ('vr', 'va') else None

        # Atualizar/criar conta de crédito
        if sc:
            account = _get_or_create_account(card.user_id, bank, lim)
            card.account_id = account.id if account else None
            # Atualizar limite na conta se fornecido
            if account and lim:
                account.credit_limit = lim
        else:
            card.account_id = None
        db.session.commit()
        flash('Cartão atualizado com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
    return redirect(url_for('cards.index'))


@cards_bp.route('/delete/<int:card_id>', methods=['POST'])
def delete(card_id):
    uids = tenant_user_ids()
    card = CreditCard.query.filter(CreditCard.id == card_id,
                                   CreditCard.user_id.in_(uids)).first_or_404()
    Expense.query.filter_by(card_id=card.id).update({'card_id': None})
    db.session.delete(card)
    db.session.commit()
    flash('Cartão excluído. As despesas vinculadas foram mantidas.', 'warning')
    return redirect(url_for('cards.index'))


@cards_bp.route('/api/info/<int:card_id>')
def api_card_info(card_id):
    uids = tenant_user_ids()
    card = CreditCard.query.filter(CreditCard.id == card_id,
                                   CreditCard.user_id.in_(uids)).first_or_404()
    return jsonify({
        'id': card.id, 'bank': card.bank or '',
        'last_digits': card.last_digits,
        'due_day': card.due_day, 'best_buy_day': card.best_buy_day,
        'label': card.label,
    })


@cards_bp.route('/api/invoice-preview')
def api_invoice_preview():
    """
    Retorna preview da fatura para uma compra específica.
    Params: card_id, day, month, year, amount (opcional)
    """
    from datetime import date as _date
    uids    = tenant_user_ids()
    card_id = request.args.get('card_id', type=int)
    day     = request.args.get('day',   type=int)
    month   = request.args.get('month', type=int)
    year    = request.args.get('year',  type=int)
    amount  = request.args.get('amount', type=float, default=0.0)

    if not all([card_id, day, month, year]):
        return jsonify({'error': 'params required'}), 400

    card = CreditCard.query.filter(
        CreditCard.id == card_id,
        CreditCard.user_id.in_(uids),
    ).first()
    if not card:
        return jsonify({'error': 'card not found'}), 404

    try:
        purchase_date = _date(year, month, day)
    except ValueError:
        return jsonify({'error': 'invalid date'}), 400

    inv_year, inv_month = get_invoice_reference(purchase_date, card.best_buy_day)
    is_open = purchase_date.day <= card.best_buy_day
    days_to_closing = (card.best_buy_day - purchase_date.day) if is_open else None

    # Limite e uso no nível da CONTA (compartilhado entre cartões do mesmo grupo)
    credit_limit = card.effective_limit
    if credit_limit:
        if card.account_id:
            current_usage = account_credit_usage(card.account_id, inv_month, inv_year)
        else:
            current_usage = credit_invoice_total(card.id, inv_month, inv_year)
    else:
        current_usage = None

    projected = (current_usage + amount) if (current_usage is not None and amount) else current_usage

    # Info da conta para contexto
    account_label = None
    account_total_cards = 1
    if card.account_id and card.account:
        account_label       = card.account.display_label
        account_total_cards = card.account.cards.count()

    return jsonify({
        'invoice_month':      get_invoice_label(inv_year, inv_month),
        'invoice_year':       inv_year,
        'invoice_month_num':  inv_month,
        'is_open':            is_open,
        'days_to_closing':    days_to_closing,
        'due_day':            card.due_day,
        'current_usage':      current_usage,
        'credit_limit':       credit_limit,
        'projected_usage':    projected,
        'account_label':      account_label,
        'account_total_cards': account_total_cards,
        'is_shared_limit':    account_total_cards > 1,
    })
