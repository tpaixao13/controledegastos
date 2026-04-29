import logging
from flask import Flask, session, redirect, url_for, request as flask_request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import text
from config import config

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_name='default'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    if not app.config.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY deve ser definida via variável de ambiente")

    db.init_app(app)
    csrf.init_app(app)

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
        _seed_users()

        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.expenses import expenses_bp
        from app.routes.salaries import salaries_bp
        from app.routes.api import api_bp
        from app.routes.investments import investments_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(expenses_bp)
        app.register_blueprint(salaries_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(investments_bp)

    @app.before_request
    def require_login():
        exempt = {'auth.login', 'auth.logout', 'auth.register', 'auth.tenant_users_api', 'static'}
        if flask_request.endpoint not in exempt and not session.get('logged_in'):
            return redirect(url_for('auth.login'))

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
            # Check if the unique constraint still exists in the table definition
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


def _seed_users():
    from app.models import User
    defaults = [('Tiago', 'tiago'), ('Greyce', 'greyce')]
    for name, pwd in defaults:
        user = User.query.filter_by(name=name).first()
        if not user:
            user = User(name=name)
            db.session.add(user)
            db.session.flush()
        if not user.password_hash:
            user.set_password(pwd)
            logging.warning(
                "Usuário '%s' criado com senha padrão fraca. "
                "Altere a senha em /profile imediatamente.", name
            )
    db.session.commit()
