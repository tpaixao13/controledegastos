from flask import session
from app.models import User

MONTH_NAMES_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                     'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

MONTH_NAMES_FULL = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


def tenant_users():
    tid = session.get('tenant_id')
    return User.query.filter_by(tenant_id=tid)


def tenant_user_ids():
    return [u.id for u in tenant_users().all()]
