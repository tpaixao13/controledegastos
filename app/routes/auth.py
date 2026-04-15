from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.models import User
from app.forms import LoginForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('main.index'))

    users = User.query.order_by(User.name).all()
    form = LoginForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    if form.validate_on_submit():
        user = User.query.get(form.user_id.data)
        if user and user.check_password(form.password.data):
            session['logged_in'] = True
            session['user_name'] = user.name
            session['user_id'] = user.id
            return redirect(url_for('main.index'))
        flash('Senha incorreta.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
