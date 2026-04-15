from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import User, Investment
from app.forms import InvestmentForm
from datetime import datetime

investments_bp = Blueprint('investments', __name__, url_prefix='/investments')


@investments_bp.route('/', methods=['GET', 'POST'])
def manage():
    users = User.query.order_by(User.name).all()
    form = InvestmentForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    now = datetime.now()
    if request.method == 'GET':
        form.year.data = now.year
        form.month.data = now.month

    if form.validate_on_submit():
        inv = Investment(
            user_id=form.user_id.data,
            description=form.description.data or None,
            amount=form.amount.data,
            investment_type=form.investment_type.data,
            annual_rate=form.annual_rate.data or 0,
            crypto_coin=form.crypto_coin.data if form.investment_type.data == 'Criptomoedas' else None,
            crypto_buy_price=float(form.crypto_buy_price.data) if form.investment_type.data == 'Criptomoedas' and form.crypto_buy_price.data else None,
            year=form.year.data,
            month=form.month.data,
        )
        db.session.add(inv)
        db.session.commit()
        flash('Investimento registrado com sucesso!', 'success')
        return redirect(url_for('investments.manage'))

    investments = (Investment.query
                   .join(User)
                   .order_by(Investment.year.desc(), Investment.month.desc())
                   .all())

    fixed_investments = [i for i in investments if not i.crypto_coin]
    crypto_investments = [i for i in investments if i.crypto_coin]

    return render_template('investments/manage.html',
                           form=form, investments=investments, users=users,
                           fixed_investments=fixed_investments,
                           crypto_investments=crypto_investments)


@investments_bp.route('/delete/<int:inv_id>', methods=['POST'])
def delete(inv_id):
    inv = Investment.query.get_or_404(inv_id)
    db.session.delete(inv)
    db.session.commit()
    flash('Investimento removido.', 'warning')
    return redirect(url_for('investments.manage'))
