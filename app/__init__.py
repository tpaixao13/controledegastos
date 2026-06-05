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
        from app.routes.cards import cards_bp
        from app.routes.rules import rules_bp
        from app.routes.alerts import alerts_bp
        from app.routes.goals import goals_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(expenses_bp)
        app.register_blueprint(salaries_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(investments_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(cards_bp)
        app.register_blueprint(rules_bp)
        app.register_blueprint(alerts_bp)
        app.register_blueprint(goals_bp)

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
    def inject_alert_count():
        """Conta alertas críticos para exibir o badge na topbar."""
        if not session.get('logged_in') or not session.get('tenant_id'):
            return {'alert_count': 0}
        try:
            from app.utils import tenant_users as _tu, get_month_year as _gmy
            from app.models import User as _U
            from app.services.alert_service import quick_alert_count
            _users = _tu().all()
            _uids  = [u.id for u in _users]
            _month, _year = _gmy()
            return {'alert_count': quick_alert_count(_uids, _month, _year)}
        except Exception:
            return {'alert_count': 0}

    @app.context_processor
    def inject_expense_modal():
        """Dados para o modal de nova despesa (disponível em todas as páginas logadas)."""
        import json as _json
        if not session.get('logged_in') or not session.get('tenant_id'):
            return {}
        try:
            from app.utils import tenant_users as _tu
            from app.models import CreditCard as _CC, User as _U
            from app.forms import CATEGORIES as _CATS
            _users = _tu().order_by(_U.name).all()
            _uids  = [u.id for u in _users]
            _cards = _CC.query.filter(_CC.user_id.in_(_uids)).order_by(_CC.bank).all()
            _card_json = _json.dumps({
                c.id: {
                    'due_day':         c.due_day,
                    'best_buy_day':    c.best_buy_day,
                    'bank':            c.bank or '',
                    'label':           c.label,
                    'credit_limit':    c.effective_limit,
                    'account_id':      c.account_id,
                    'card_type':       c.card_type or '',
                    'supports_credit': bool(c.supports_credit),
                    'supports_debit':  bool(c.supports_debit),
                    'is_virtual':      bool(c.is_virtual),
                    'is_additional':   bool(c.is_additional),
                    'monthly_amount':  float(c.monthly_amount) if c.monthly_amount else None,
                }
                for c in _cards
            })
            return {
                'modal_users':         _users,
                'modal_cards':         _cards,
                'modal_card_data_json': _card_json,
                'modal_categories':    sorted([c[0] for c in _CATS]),
            }
        except Exception:
            return {}

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        from app.models import Tenant
        now = datetime.now()
        base = {'now': now, 'trial_days_left': None, 'current_plan': None}
        tenant_id = session.get('tenant_id')
        if not tenant_id:
            return base
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return base
        plan = tenant.plan or 'trial'
        if tenant.trial_expires_at is None:
            base.update({'current_plan': plan})
            return base
        delta = (tenant.trial_expires_at - datetime.utcnow()).days
        base.update({'trial_days_left': max(0, delta), 'current_plan': plan})
        return base

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
                from datetime import timedelta
                user = User.query.get(user_id)
                if user and (not user.last_seen or
                             datetime.now() - user.last_seen > timedelta(minutes=1)):
                    user.last_seen = datetime.now()
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
        "ALTER TABLE salaries ADD COLUMN income_type TEXT NOT NULL DEFAULT 'fixa'",
        "CREATE TABLE IF NOT EXISTS salary_groups (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created_at DATETIME)",
        "ALTER TABLE salaries ADD COLUMN salary_group_id INTEGER REFERENCES salary_groups(id)",
        "ALTER TABLE salaries ADD COLUMN payment_day INTEGER",
        "ALTER TABLE salaries ADD COLUMN payment_day_type TEXT",
        "ALTER TABLE salaries ADD COLUMN received INTEGER DEFAULT 1",
        "ALTER TABLE tenants ADD COLUMN plan TEXT DEFAULT 'trial'",
        "ALTER TABLE tenants ADD COLUMN extra_members INTEGER DEFAULT 0",
        "CREATE TABLE IF NOT EXISTS credit_cards (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), nickname TEXT, last_digits TEXT NOT NULL, bank TEXT, due_day INTEGER NOT NULL, best_buy_day INTEGER NOT NULL, created_at DATETIME)",
        "ALTER TABLE expenses ADD COLUMN card_id INTEGER REFERENCES credit_cards(id)",
        "ALTER TABLE credit_cards ADD COLUMN credit_limit NUMERIC(12,2)",
        "CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL, type TEXT NOT NULL, target_amount NUMERIC(12,2) NOT NULL, category TEXT, due_date DATE, start_date DATE NOT NULL, created_at DATETIME, completed_at DATETIME, active INTEGER NOT NULL DEFAULT 1)",
        "CREATE TABLE IF NOT EXISTS category_rules (id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES tenants(id), keyword TEXT NOT NULL, category TEXT NOT NULL, match_count INTEGER NOT NULL DEFAULT 0, created_at DATETIME)",
        "ALTER TABLE credit_cards ADD COLUMN card_type TEXT NOT NULL DEFAULT 'credit'",
        "ALTER TABLE credit_cards ADD COLUMN is_virtual INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE credit_cards ADD COLUMN is_additional INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE credit_cards ADD COLUMN monthly_amount NUMERIC(12,2)",
        "ALTER TABLE credit_cards ADD COLUMN renewal_day INTEGER",
        "ALTER TABLE credit_cards ADD COLUMN supports_credit INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE credit_cards ADD COLUMN supports_debit INTEGER NOT NULL DEFAULT 0",
        # Migração de dados: converter card_type legado para supports_*
        "UPDATE credit_cards SET supports_credit = 1 WHERE card_type = 'credit' AND supports_credit = 0",
        "UPDATE credit_cards SET supports_debit = 1 WHERE card_type = 'debit' AND supports_debit = 0",
        # CreditAccount — linha de crédito compartilhada
        "CREATE TABLE IF NOT EXISTS credit_accounts (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), bank TEXT, label TEXT, credit_limit NUMERIC(12,2), created_at DATETIME)",
        "ALTER TABLE credit_cards ADD COLUMN account_id INTEGER REFERENCES credit_accounts(id)",
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

        # Seed known emails for existing users (lidos do .env — sem PII no código)
        try:
            tiago_email  = os.environ.get('SEED_EMAIL_TIAGO', '')
            greyce_email = os.environ.get('SEED_EMAIL_GREYCE', '')
            if tiago_email:
                conn.execute(text(
                    "UPDATE users SET email=:e WHERE name='Tiago' AND (email IS NULL OR email='')"
                ), {'e': tiago_email})
            if greyce_email:
                conn.execute(text(
                    "UPDATE users SET email=:e WHERE name='Greyce' AND (email IS NULL OR email='')"
                ), {'e': greyce_email})
            conn.commit()
        except Exception:
            pass

        # Seed admin user (INSERT OR IGNORE é idempotente — não sobrescreve senha existente)
        try:
            import secrets as _secrets
            from werkzeug.security import generate_password_hash
            admin_pw = os.environ.get('ADMIN_INITIAL_PASSWORD')
            if not admin_pw:
                admin_pw = _secrets.token_urlsafe(16)
                print(f'[FinFam] AVISO: ADMIN_INITIAL_PASSWORD não definida. '
                      f'Senha gerada para admin@finfam.app: {admin_pw}')
            conn.execute(text(
                "INSERT OR IGNORE INTO users (name, email, password_hash, is_admin) "
                "VALUES ('Admin', 'admin@finfam.app', :pw, 1)"
            ), {'pw': generate_password_hash(admin_pw)})
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

        # Migração de dados: criar CreditAccount para cartões sem conta
        _migrate_credit_accounts(conn)


def _migrate_credit_accounts(conn):
    """
    Agrupa cartões de crédito pelo (user_id, bank) e cria CreditAccount
    para cada grupo. Move o maior credit_limit para a conta.
    Idempotente: não recria contas já existentes.
    """
    try:
        # Cartões de crédito ainda não vinculados a uma conta
        unlinked = conn.execute(text(
            "SELECT DISTINCT user_id, bank "
            "FROM credit_cards "
            "WHERE account_id IS NULL AND supports_credit = 1 AND bank IS NOT NULL"
        )).fetchall()

        for row in unlinked:
            uid, bank = row[0], row[1]

            # Verificar se já existe conta para (user_id, bank)
            existing = conn.execute(text(
                "SELECT id FROM credit_accounts WHERE user_id = :uid AND bank = :bank"
            ), {'uid': uid, 'bank': bank}).fetchone()

            if existing:
                account_id = existing[0]
            else:
                # Herdar o maior limite dentre os cartões do grupo
                max_limit = conn.execute(text(
                    "SELECT MAX(credit_limit) FROM credit_cards "
                    "WHERE user_id = :uid AND bank = :bank AND supports_credit = 1"
                ), {'uid': uid, 'bank': bank}).scalar()

                conn.execute(text(
                    "INSERT INTO credit_accounts (user_id, bank, credit_limit, created_at) "
                    "VALUES (:uid, :bank, :lim, CURRENT_TIMESTAMP)"
                ), {'uid': uid, 'bank': bank, 'lim': max_limit})
                conn.commit()

                account_id = conn.execute(text(
                    "SELECT id FROM credit_accounts WHERE user_id = :uid AND bank = :bank"
                ), {'uid': uid, 'bank': bank}).scalar()

            # Vincular todos os cartões do grupo à conta
            conn.execute(text(
                "UPDATE credit_cards SET account_id = :aid "
                "WHERE user_id = :uid AND bank = :bank "
                "AND supports_credit = 1 AND account_id IS NULL"
            ), {'aid': account_id, 'uid': uid, 'bank': bank})
            conn.commit()

    except Exception:
        pass


