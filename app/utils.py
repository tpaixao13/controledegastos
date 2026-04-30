import json
import ssl
import time
import urllib.request
from flask import session
from app.models import User

MONTH_NAMES_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                     'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

# Paleta por ordem de cadastro — suporta até 6 usuários por tenant
USER_PALETTE = [
    {'card_class': 'card-user-0', 'badge_class': 'bg-primary',            'hex': '#0d6efd', 'hex_alpha': 'rgba(13,110,253,0.7)'},
    {'card_class': 'card-user-1', 'badge_class': 'bg-danger',             'hex': '#dc3545', 'hex_alpha': 'rgba(220,53,69,0.7)'},
    {'card_class': 'card-user-2', 'badge_class': 'bg-success',            'hex': '#198754', 'hex_alpha': 'rgba(25,135,84,0.7)'},
    {'card_class': 'card-user-3', 'badge_class': 'bg-warning text-dark',  'hex': '#ffc107', 'hex_alpha': 'rgba(255,193,7,0.7)'},
    {'card_class': 'card-user-4', 'badge_class': 'bg-info text-dark',     'hex': '#0dcaf0', 'hex_alpha': 'rgba(13,202,240,0.7)'},
    {'card_class': 'card-user-5', 'badge_class': 'bg-secondary',          'hex': '#6c757d', 'hex_alpha': 'rgba(108,117,125,0.7)'},
]


def user_color_map(users: list) -> dict:
    """Returns {user.id: palette_entry} ordered by the users list."""
    return {u.id: USER_PALETTE[i % len(USER_PALETTE)] for i, u in enumerate(users)}

MONTH_NAMES_FULL = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

_SELIC_URL = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json'
SELIC_FALLBACK = 14.75

_cache: dict = {}
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def tenant_users():
    tid = session.get('tenant_id')
    return User.query.filter_by(tenant_id=tid)


def tenant_user_ids():
    return [u.id for u in tenant_users().all()]


def month_offset(base_month: int, base_year: int, offset: int) -> tuple[int, int]:
    """Returns (month, year) shifted by `offset` months from base."""
    m = (base_month - 1 + offset) % 12 + 1
    y = base_year + ((base_month - 1 + offset) // 12)
    return m, y


def _fetch_json(url: str, cache_key: str, ttl: int = 3600):
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]['ts'] < ttl:
        return _cache[cache_key]['data']
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ControleGastos/1.0)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
        # purge entradas expiradas há mais de 2h para evitar crescimento ilimitado
        stale = [k for k, v in _cache.items() if now - v['ts'] > 7200]
        for k in stale:
            del _cache[k]
        _cache[cache_key] = {'data': data, 'ts': now}
        return data
    except Exception as e:
        print(f'[_fetch_json] Erro ao buscar {url}: {e}')
        return None


def get_selic_rate() -> float:
    data = _fetch_json(_SELIC_URL, 'selic')
    if data:
        try:
            return float(data[0]['valor'].replace(',', '.'))
        except Exception:
            pass
    return SELIC_FALLBACK


def rate_suggestions(selic: float) -> dict:
    return {
        'Tesouro Selic':       round(selic, 2),
        'CDB':                 round(selic, 2),
        'LCI':                 round(selic * 0.87, 2),
        'LCA':                 round(selic * 0.87, 2),
        'CRI/CRA':             round(selic * 0.95, 2),
        'Debêntures':          round(selic * 1.05, 2),
        'COE':                 round(selic * 0.90, 2),
        'Fundo de Renda Fixa': round(selic * 0.95, 2),
        'Fundo Multimercado':  round(selic * 1.10, 2),
        'Tesouro IPCA+':       round(selic * 0.60, 2),
        'Tesouro Prefixado':   round(selic * 0.95, 2),
        'Poupança':            round(selic * 0.70, 2),
        'Ações':               0,
        'FIIs':                0,
        'Criptomoedas':        0,
        'Outros':              0,
    }


# ── Helpers de agregação (evitam N queries em loops) ─────────────────────────

def sum_expenses_month(uids: list, year: int, month: int, *extra_filters) -> float:
    """Soma Expense.amount para o tenant no mês. Aceita filtros SQLAlchemy extras."""
    from app import db
    from app.models import Expense
    from sqlalchemy import func
    q = (db.session.query(func.sum(Expense.amount))
         .filter(Expense.user_id.in_(uids), Expense.year == year,
                 Expense.month == month, *extra_filters))
    return float(q.scalar() or 0)


def sum_salaries_month(uids: list, year: int, month: int) -> float:
    """Soma Salary.amount para o tenant no mês."""
    from app import db
    from app.models import Salary
    from sqlalchemy import func
    return float(
        db.session.query(func.sum(Salary.amount))
        .filter(Salary.user_id.in_(uids), Salary.year == year, Salary.month == month)
        .scalar() or 0
    )
