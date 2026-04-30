import os
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Tenant
from app.forms import LoginForm, ChangePasswordForm, AvatarForm, RegisterTenantForm, AddMemberForm

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

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            tenant = Tenant.query.get(user.tenant_id) if user.tenant_id else None
            session['logged_in'] = True
            session['user_name'] = user.name
            session['user_id'] = user.id
            session['user_avatar'] = _avatar_url(user)
            session['tenant_id'] = user.tenant_id
            session['tenant_name'] = tenant.name if tenant else ''
            return redirect(url_for('main.index'))
        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterTenantForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado. Faça login ou use outro e-mail.', 'danger')
            return render_template('auth/register.html', form=form)

        code = secrets.token_hex(8)
        first_name = form.user_name.data.strip().split()[0]
        tenant = Tenant(name=f'Família {first_name}', code=code)
        db.session.add(tenant)
        db.session.flush()

        user = User(name=form.user_name.data.strip(), email=email, tenant_id=tenant.id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Conta criada com sucesso! Faça login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
def profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    return render_template('auth/profile.html', user=user,
                           pwd_form=ChangePasswordForm(prefix='pwd'),
                           avatar_form=AvatarForm(prefix='av'))


@auth_bp.route('/profile/password', methods=['POST'])
def change_password():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    pwd_form = ChangePasswordForm(prefix='pwd')
    if pwd_form.validate_on_submit():
        if not user.check_password(pwd_form.current_password.data):
            pwd_form.current_password.errors.append('Senha atual incorreta.')
        else:
            user.set_password(pwd_form.new_password.data)
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html', user=user,
                           pwd_form=pwd_form,
                           avatar_form=AvatarForm(prefix='av'))


@auth_bp.route('/profile/avatar', methods=['POST'])
def upload_avatar():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    avatar_form = AvatarForm(prefix='av')
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
                           pwd_form=ChangePasswordForm(prefix='pwd'),
                           avatar_form=avatar_form)


@auth_bp.route('/members', methods=['GET', 'POST'])
def members():
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        return redirect(url_for('auth.login'))
    tenant = Tenant.query.get(tenant_id)
    form = AddMemberForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.', 'danger')
        else:
            user = User(name=form.user_name.data.strip(), email=email, tenant_id=tenant_id)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f'{form.user_name.data.strip()} adicionado com sucesso!', 'success')
            return redirect(url_for('auth.members'))

    member_list = User.query.filter_by(tenant_id=tenant_id).order_by(User.name).all()
    return render_template('auth/members.html', form=form, tenant=tenant, members=member_list)


@auth_bp.route('/members/delete/<int:user_id>', methods=['POST'])
def delete_member(user_id):
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        return redirect(url_for('auth.login'))
    if user_id == session.get('user_id'):
        flash('Você não pode remover a si mesmo.', 'danger')
        return redirect(url_for('auth.members'))

    user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first_or_404()
    db.session.delete(user)
    db.session.commit()
    flash(f'{user.name} removido do grupo.', 'warning')
    return redirect(url_for('auth.members'))
