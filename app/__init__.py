import logging
import os
import shutil
import sys
from flask import Flask, session, redirect, url_for, request as flask_request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import text
from config import config

db = SQLAlchemy()
csrf = CSRFProtect()

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address, default_limits=[])
except ImportError:
    limiter = None


def create_app(config_name='default'):
    if getattr(sys, 'frozen', False):
        # Rodando como .exe gerado pelo PyInstaller
        _bundle = sys._MEIPASS
        _appdata = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')), 'FinFam'
        )
        _user_static = os.path.join(_appdata, 'static')

        # Copia static (css/js/images) para APPDATA na primeira execução
        # para que uploads de avatar também funcionem nessa pasta
        if not os.path.exists(_user_static):
            shutil.copytree(
                os.path.join(_bundle, 'app', 'static'),
                _user_static,
            )

        app = Flask(
            __name__,
            template_folder=os.path.join(_bundle, 'app', 'templates'),
            static_folder=_user_static,
            instance_relative_config=False,
        )
    else:
        app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    if not app.config.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY deve ser definida via variável de ambiente")

    db.init_app(app)
    csrf.init_app(app)
    if limiter:
        limiter.init_app(app)

    # Filtro Jinja2 para formatar moeda BRL
    @app.template_filter('brl')
    def brl_filter(value):
        try:
            return f'R$ {float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        except (TypeError, ValueError):
            return 'R$ 0,00'

    # Filtro para nome do mês
    @app.template_filter('mes_nome')
    def mes_nome_filter(value):
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        try:
            return meses[int(value) - 1]
        except (TypeError, ValueError, IndexError):
            return str(value)

    with app.app_context():
        from app import models
        db.create_all()
        _run_migrations()

        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.expenses import expenses_bp
        from app.routes.salaries import salaries_bp
        from app.routes.api import api_bp
        from app.routes.investments import investments_bp
        from app.routes.admin import admin_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(expenses_bp)
        app.register_blueprint(salaries_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(investments_bp)
        app.register_blueprint(admin_bp)

        if limiter:
            limiter.limit('20 per minute')(app.view_functions['auth.login'])
            limiter.limit('10 per minute')(app.view_functions['admin.login'])

    # Scheduler de lembretes Telegram — roda às 8h todos os dias
    import atexit
    import os
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.utils import send_daily_reminders
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            _scheduler = BackgroundScheduler()
            _scheduler.add_job(send_daily_reminders, 'interval', args=[app], minutes=1)
            _scheduler.start()
            atexit.register(lambda: _scheduler.shutdown(wait=False))
    except ImportError:
        logging.warning('APScheduler não instalado — lembretes Telegram desativados.')

    @app.context_processor
    def inject_trial():
        from datetime import datetime
        from app.models import Tenant
        tenant_id = session.get('tenant_id')
        if not tenant_id:
            return {'trial_days_left': None}
        tenant = Tenant.query.get(tenant_id)
        if not tenant or tenant.trial_expires_at is None:
            return {'trial_days_left': None}
        delta = (tenant.trial_expires_at - datetime.utcnow()).days
        return {'trial_days_left': max(0, delta)}

    @app.before_request
    def require_login():
        from datetime import datetime
        from app.models import Tenant
        exempt = {'auth.login', 'auth.logout', 'auth.register', 'auth.trial_expired', 'static'}
        endpoint = flask_request.endpoint or ''
        if endpoint.startswith('admin.') or flask_request.path.startswith('/admin'):
            return
        if endpoint not in exempt and not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        if session.get('logged_in') and endpoint not in exempt:
            tenant_id = session.get('tenant_id')
            if tenant_id:
                tenant = Tenant.query.get(tenant_id)
                if tenant and tenant.trial_expires_at and datetime.utcnow() > tenant.trial_expires_at:
                    session.clear()
                    return redirect(url_for('auth.trial_expired'))
            user_id = session.get('user_id')
            if user_id:
                from app.models import User
                User.query.filter_by(id=user_id).update({'last_seen': datetime.utcnow()})
                db.session.commit()

    return app


def _run_migrations():
    """Adiciona colunas novas ao schema existente sem perder dados."""
    migrations = [
        'ALTER TABLE users ADD COLUMN password_hash TEXT',
        'ALTER TABLE expenses ADD COLUMN recurring_group_id INTEGER REFERENCES recurring_groups(id)',
        'ALTER TABLE expenses ADD COLUMN recurring_number INTEGER',
        'ALTER TABLE users ADD COLUMN avatar TEXT',
        'ALTER TABLE expenses ADD COLUMN paid INTEGER DEFAULT 0',
        'ALTER TABLE salaries ADD COLUMN company TEXT',
        'ALTER TABLE investments ADD COLUMN crypto_coin TEXT',
        'ALTER TABLE investments ADD COLUMN crypto_buy_price NUMERIC(18,8)',
        "CREATE TABLE IF NOT EXISTS tenants (id INTEGER PRIMARY KEY, name TEXT NOT NULL, code TEXT NOT NULL UNIQUE, created_at DATETIME)",
        'ALTER TABLE users ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)',
        'ALTER TABLE users ADD COLUMN email TEXT',
        'ALTER TABLE tenants ADD COLUMN telegram_enabled INTEGER DEFAULT 0',
        'ALTER TABLE tenants ADD COLUMN telegram_token TEXT',
        'ALTER TABLE tenants ADD COLUMN telegram_chat_id TEXT',
        'ALTER TABLE tenants ADD COLUMN telegram_hour INTEGER DEFAULT 8',
        'ALTER TABLE tenants ADD COLUMN telegram_minute INTEGER DEFAULT 0',
        'ALTER TABLE tenants ADD COLUMN trial_expires_at DATETIME',
        'ALTER TABLE tenants ADD COLUMN telegram_last_sent DATE',
        'ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0',
        'ALTER TABLE users ADD COLUMN last_seen DATETIME',
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # coluna já existe

        # Remove unique constraint on salaries (SQLite requires table recreation)
        try:
            row = conn.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='salaries'"
            )).fetchone()
            if row and 'UNIQUE' in row[0].upper():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS salaries_new (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        year INTEGER NOT NULL,
                        month INTEGER NOT NULL,
                        amount NUMERIC(12,2) NOT NULL,
                        company TEXT
                    )
                """))
                conn.execute(text(
                    "INSERT INTO salaries_new (id, user_id, year, month, amount, company) "
                    "SELECT id, user_id, year, month, amount, company FROM salaries"
                ))
                conn.execute(text("DROP TABLE salaries"))
                conn.execute(text("ALTER TABLE salaries_new RENAME TO salaries"))
                conn.commit()
        except Exception:
            pass

        # Remove unique constraint on users.name (multi-tenant: same name allowed in different tenants)
        try:
            row = conn.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
            )).fetchone()
            if row and 'UNIQUE' in row[0].upper():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users_new (
                        id INTEGER PRIMARY KEY,
                        tenant_id INTEGER REFERENCES tenants(id),
                        name TEXT NOT NULL,
                        email TEXT UNIQUE,
                        password_hash TEXT,
                        avatar TEXT
                    )
                """))
                conn.execute(text(
                    "INSERT INTO users_new (id, tenant_id, name, password_hash, avatar) "
                    "SELECT id, tenant_id, name, password_hash, avatar FROM users"
                ))
                conn.execute(text("DROP TABLE users"))
                conn.execute(text("ALTER TABLE users_new RENAME TO users"))
                conn.commit()
        except Exception:
            pass

        # Seed known emails for existing users (safe — no-op if already set or user absent)
        try:
            conn.execute(text(
                "UPDATE users SET email='tiagopedro376@hotmail.com' "
                "WHERE name='Tiago' AND (email IS NULL OR email='')"
            ))
            conn.execute(text(
                "UPDATE users SET email='jovemgreyce@hotmail.com' "
                "WHERE name='Greyce' AND (email IS NULL OR email='')"
            ))
            conn.commit()
        except Exception:
            pass

        # Seed admin user (INSERT OR IGNORE is idempotent)
        try:
            from werkzeug.security import generate_password_hash
            conn.execute(text(
                "INSERT OR IGNORE INTO users (name, email, password_hash, is_admin) "
                "VALUES ('Admin', 'admin@finfam.app', :pw, 1)"
            ), {'pw': generate_password_hash('FinFam@Admin2025')})
            conn.execute(text(
                "UPDATE users SET is_admin=1 WHERE email='admin@finfam.app'"
            ))
            conn.commit()
        except Exception:
            pass

        # Set test1@tste.com.br trial to 10 days from now
        try:
            conn.execute(text("""
                UPDATE tenants SET trial_expires_at=datetime('now', '+10 days')
                WHERE id IN (
                    SELECT tenant_id FROM users WHERE email='teste1@tste.com.br'
                )
            """))
            conn.commit()
        except Exception:
            pass


