from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import User, Investment
from app.forms import InvestmentForm
from app.utils import tenant_users, tenant_user_ids, _fetch_json, get_selic_rate, rate_suggestions, user_color_map
from datetime import datetime

investments_bp = Blueprint('investments', __name__, url_prefix='/investments')


def _fetch_crypto_price(coin):
    data = _fetch_json(
        f'https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=brl',
        f'crypto_price_{coin}',
        ttl=300,
    )
    if data and coin in data:
        return float(data[coin]['brl'])
    return None


@investments_bp.route('/', methods=['GET', 'POST'])
def manage():
    users = tenant_users().order_by(User.name).all()
    form = InvestmentForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    now = datetime.now()
    if request.method == 'GET':
        form.year.data = now.year
        form.month.data = now.month

    if form.validate_on_submit():
        is_crypto = form.investment_type.data == 'Criptomoedas'
        coin = form.crypto_coin.data if is_crypto else None

        # Preço de compra: usa o enviado pelo JS, ou busca no servidor como fallback
        buy_price = None
        if is_crypto and coin:
            raw = form.crypto_buy_price.data
            if raw:
                try:
                    buy_price = float(raw)
                except (ValueError, TypeError):
                    pass
            if not buy_price:
                buy_price = _fetch_crypto_price(coin)

        inv = Investment(
            user_id=form.user_id.data,
            description=form.description.data or None,
            amount=form.amount.data,
            investment_type=form.investment_type.data,
            annual_rate=form.annual_rate.data or 0,
            crypto_coin=coin,
            crypto_buy_price=buy_price,
            year=form.year.data,
            month=form.month.data,
        )
        db.session.add(inv)
        db.session.commit()
        flash('Investimento registrado com sucesso!', 'success')
        return redirect(url_for('investments.manage'))

    uids = [u.id for u in users]
    investments = (Investment.query
                   .filter(Investment.user_id.in_(uids))
                   .join(User)
                   .order_by(Investment.year.desc(), Investment.month.desc())
                   .all())

    fixed_investments = [i for i in investments if not i.crypto_coin]
    crypto_investments = [i for i in investments if i.crypto_coin]

    selic = get_selic_rate()

    return render_template('investments/manage.html',
                           form=form, investments=investments, users=users,
                           fixed_investments=fixed_investments,
                           crypto_investments=crypto_investments,
                           selic=selic,
                           rate_suggestions=rate_suggestions(selic))


@investments_bp.route('/delete/<int:inv_id>', methods=['POST'])
def delete(inv_id):
    uids = tenant_user_ids()
    inv = Investment.query.filter(Investment.id == inv_id, Investment.user_id.in_(uids)).first_or_404()
    db.session.delete(inv)
    db.session.commit()
    flash('Investimento removido.', 'warning')
    return redirect(url_for('investments.manage'))
