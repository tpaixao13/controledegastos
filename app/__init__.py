from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
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
        _seed_users()

        from app.routes.main import main_bp
        from app.routes.expenses import expenses_bp
        from app.routes.salaries import salaries_bp
        from app.routes.api import api_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(expenses_bp)
        app.register_blueprint(salaries_bp)
        app.register_blueprint(api_bp)

    return app


def _seed_users():
    from app.models import User
    for name in ['Tiago', 'Greyce']:
        if not User.query.filter_by(name=name).first():
            db.session.add(User(name=name))
    db.session.commit()
