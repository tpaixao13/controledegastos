from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import User, Investment
from app.forms import InvestmentForm
from app.utils import tenant_users, tenant_user_ids
from datetime import datetime
import urllib.request
import json
import ssl

investments_bp = Blueprint('investments', __name__, url_prefix='/investments')

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _fetch_selic():
    """Busca taxa Selic atual do BCB. Retorna float (ex: 14.75)."""
    try:
        url = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=5, context=_ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        return float(data[0]['valor'].replace(',', '.'))
    except Exception:
        return 14.75  # fallback


def _fetch_crypto_price(coin):
    """Busca preço atual de uma crypto em BRL via CoinGecko."""
    try:
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=brl'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        return float(data[coin]['brl'])
    except Exception:
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

    selic = _fetch_selic()
    rate_suggestions = {
        'Tesouro Selic': round(selic, 2),
        'CDB': round(selic, 2),
        'LCI': round(selic * 0.87, 2),
        'LCA': round(selic * 0.87, 2),
        'CRI/CRA': round(selic * 0.95, 2),
        'Debêntures': round(selic * 1.05, 2),
        'COE': round(selic * 0.90, 2),
        'Fundo de Renda Fixa': round(selic * 0.95, 2),
        'Fundo Multimercado': round(selic * 1.10, 2),
        'Tesouro IPCA+': round(selic * 0.60, 2),
        'Tesouro Prefixado': round(selic * 0.95, 2),
        'Poupança': round(selic * 0.70, 2),
    }

    return render_template('investments/manage.html',
                           form=form, investments=investments, users=users,
                           fixed_investments=fixed_investments,
                           crypto_investments=crypto_investments,
                           selic=selic,
                           rate_suggestions=rate_suggestions)


@investments_bp.route('/delete/<int:inv_id>', methods=['POST'])
def delete(inv_id):
    inv = Investment.query.get_or_404(inv_id)
    db.session.delete(inv)
    db.session.commit()
    flash('Investimento removido.', 'warning')
    return redirect(url_for('investments.manage'))
