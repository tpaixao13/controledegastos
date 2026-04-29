from flask import session
from app.models import User


def tenant_users():
    tid = session.get('tenant_id')
    return User.query.filter_by(tenant_id=tid)


def tenant_user_ids():
    return [u.id for u in tenant_users().all()]
