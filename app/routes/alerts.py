from flask import Blueprint, render_template, session
from app.models import CreditCard
from app.utils import tenant_user_ids, get_month_year
from app.services.alert_service import generate_alerts

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')

MONTH_NAMES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
               'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


@alerts_bp.route('/')
def index():
    uids      = tenant_user_ids()
    tenant_id = session.get('tenant_id')
    month, year = get_month_year()

    cards = CreditCard.query.filter(CreditCard.user_id.in_(uids)).all()
    alerts = generate_alerts(uids, month, year, tenant_id, cards=cards)

    n_danger  = sum(1 for a in alerts if a['type'] == 'danger')
    n_warning = sum(1 for a in alerts if a['type'] == 'warning')

    return render_template('alerts/index.html',
                           alerts=alerts,
                           month=month, year=year,
                           month_name=MONTH_NAMES[month - 1],
                           n_danger=n_danger,
                           n_warning=n_warning)
