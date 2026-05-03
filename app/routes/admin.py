from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, Tenant

ONLINE_THRESHOLD = timedelta(minutes=5)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _require_admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))


@admin_bp.before_request
def check_admin():
    if request.endpoint == 'admin.login':
        return
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email, is_admin=True).first()
        if user and user.check_password(password):
            session['admin_logged_in'] = True
            session['admin_name'] = user.name
            session['admin_id'] = user.id
            return redirect(url_for('admin.dashboard'))
        error = 'Credenciais inválidas.'
    return render_template('admin/login.html', error=error)


@admin_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
def dashboard():
    now = datetime.utcnow()
    tenants = (Tenant.query
               .filter(Tenant.users.any(User.is_admin == False))
               .order_by(Tenant.created_at.desc())
               .all())

    total_tenants = len(tenants)
    total_users = User.query.filter(User.is_admin == False).count()

    trial_active = [t for t in tenants if t.trial_expires_at and t.trial_expires_at > now]
    trial_expired = [t for t in tenants if t.trial_expires_at and t.trial_expires_at <= now]
    lifetime = [t for t in tenants if t.trial_expires_at is None]
    expiring_soon = [t for t in trial_active if (t.trial_expires_at - now).days <= 7]

    online_cutoff = now - ONLINE_THRESHOLD
    online_users = User.query.filter(
        User.is_admin == False,
        User.last_seen >= online_cutoff
    ).all()

    return render_template('admin/dashboard.html',
                           tenants=tenants,
                           total_tenants=total_tenants,
                           total_users=total_users,
                           trial_active=trial_active,
                           trial_expired=trial_expired,
                           lifetime=lifetime,
                           expiring_soon=expiring_soon,
                           online_users=online_users,
                           now=now)


@admin_bp.route('/reset-password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()
    if len(new_password) < 8:
        flash('A senha deve ter pelo menos 8 caracteres.', 'danger')
        return redirect(url_for('admin.dashboard'))
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash(f'Senha de {user.name} redefinida com sucesso.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/grant-lifetime/<int:tenant_id>', methods=['POST'])
def grant_lifetime(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.trial_expires_at = None
    db.session.commit()
    flash(f'Acesso vitalício concedido a "{tenant.name}".', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/revoke-lifetime/<int:tenant_id>', methods=['POST'])
def revoke_lifetime(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.trial_expires_at = datetime.utcnow() - timedelta(days=1)
    db.session.commit()
    flash(f'Acesso de "{tenant.name}" revogado.', 'warning')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    tenant = Tenant.query.get(user.tenant_id) if user.tenant_id else None
    name = user.name
    db.session.delete(user)
    db.session.flush()
    if tenant and tenant.users.filter(User.is_admin == False).count() == 0:
        db.session.delete(tenant)
    db.session.commit()
    flash(f'Utilizador "{name}" eliminado.', 'warning')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete-tenant/<int:tenant_id>', methods=['POST'])
def delete_tenant(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    name = tenant.name
    db.session.delete(tenant)
    db.session.commit()
    flash(f'Família "{name}" e todos os seus membros eliminados.', 'danger')
    return redirect(url_for('admin.dashboard'))
