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
        exempt = {'auth.login', 'auth.logout', 'static'}
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
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # coluna já existe


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
    db.session.commit()
