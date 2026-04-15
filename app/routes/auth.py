import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from werkzeug.utils import secure_filename
from app import db
from app.models import User
from app.forms import LoginForm, ChangePasswordForm, AvatarForm

auth_bp = Blueprint('auth', __name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


def _avatar_url(user):
    if user.avatar:
        return url_for('static', filename=f'uploads/avatars/{user.avatar}')
    return None


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
            session['user_avatar'] = _avatar_url(user)
            return redirect(url_for('main.index'))
        flash('Senha incorreta.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    pwd_form = ChangePasswordForm(prefix='pwd')
    avatar_form = AvatarForm(prefix='av')

    # Alterar senha
    if request.method == 'POST' and 'pwd-submit_pwd' in request.form:
        if pwd_form.validate_on_submit():
            if not user.check_password(pwd_form.current_password.data):
                pwd_form.current_password.errors.append('Senha atual incorreta.')
            else:
                user.set_password(pwd_form.new_password.data)
                db.session.commit()
                flash('Senha alterada com sucesso!', 'success')
                return redirect(url_for('auth.profile'))

    # Alterar avatar
    if request.method == 'POST' and 'av-submit_avatar' in request.form:
        if avatar_form.validate_on_submit():
            file = avatar_form.avatar.data
            if file and file.filename:
                ext = os.path.splitext(secure_filename(file.filename))[1].lower()
                if ext not in {'.' + e for e in ALLOWED_EXTENSIONS}:
                    flash('Formato de imagem não suportado.', 'danger')
                else:
                    filename = f'user_{user.id}{ext}'
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
                    os.makedirs(upload_dir, exist_ok=True)
                    # Remove avatar anterior se extensão diferente
                    for old_ext in ALLOWED_EXTENSIONS:
                        old_path = os.path.join(upload_dir, f'user_{user.id}.{old_ext}')
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    file.save(os.path.join(upload_dir, filename))
                    user.avatar = filename
                    db.session.commit()
                    session['user_avatar'] = _avatar_url(user)
                    flash('Foto atualizada com sucesso!', 'success')
                    return redirect(url_for('auth.profile'))
            else:
                flash('Selecione uma imagem.', 'warning')

    return render_template('auth/profile.html', user=user,
                           pwd_form=pwd_form, avatar_form=avatar_form)
