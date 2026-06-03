"""
card_service.py — Lógica de negócio para cartões de crédito e faturas.
"""

import calendar as _calendar
from datetime import datetime, date as _date
from sqlalchemy import func, or_, and_
from app import db
from app.models import Expense, InstallmentGroup, CreditCard, CreditAccount
from app.utils import month_offset

_PT_MONTHS = [
    '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


def get_invoice_reference(purchase_date: _date, best_buy_day: int) -> tuple[int, int]:
    """
    Retorna (year, month) da fatura em que a compra será lançada.

    Regra: se o dia da compra é posterior ao melhor dia de compra (best_buy_day),
    ela cai na fatura do próximo mês; caso contrário, cai na fatura do mês atual.
    """
    if purchase_date.day > best_buy_day:
        if purchase_date.month == 12:
            return purchase_date.year + 1, 1
        return purchase_date.year, purchase_date.month + 1
    return purchase_date.year, purchase_date.month


def get_invoice_label(year: int, month: int) -> str:
    """Retorna rótulo legível da fatura, ex: 'Julho 2026'."""
    return f"{_PT_MONTHS[month]} {year}"

# ── Gradientes por banco ────────────────────────────────────────────
BANK_GRADIENTS = {
    'Nubank':                  ('linear-gradient(135deg,#820ad1,#5c0391)', '#fff'),
    'Itaú':                    ('linear-gradient(135deg,#FF6600,#cc4400)', '#fff'),
    'Bradesco':                ('linear-gradient(135deg,#CC0000,#8b0000)', '#fff'),
    'Banco do Brasil':         ('linear-gradient(135deg,#F9C700,#c9a200)', '#212529'),
    'Santander':               ('linear-gradient(135deg,#EC0000,#a80000)', '#fff'),
    'Inter':                   ('linear-gradient(135deg,#FF7A00,#cc5e00)', '#fff'),
    'C6 Bank':                 ('linear-gradient(135deg,#232323,#000)', '#e8c840'),
    'Caixa Econômica Federal': ('linear-gradient(135deg,#005B9A,#003a6b)', '#fff'),
    'BTG Pactual':             ('linear-gradient(135deg,#1a1a2e,#0f0f1a)', '#c9a227'),
    'Sicredi':                 ('linear-gradient(135deg,#006633,#004422)', '#fff'),
    'Sicoob':                  ('linear-gradient(135deg,#006633,#004422)', '#fff'),
    'Safra':                   ('linear-gradient(135deg,#003399,#001f66)', '#fff'),
    'Original':                ('linear-gradient(135deg,#00A859,#006e3a)', '#fff'),
    'Neon':                    ('linear-gradient(135deg,#00C4B4,#008a7e)', '#fff'),
    'PicPay':                  ('linear-gradient(135deg,#21c25e,#128a3e)', '#fff'),
    'XP Investimentos':        ('linear-gradient(135deg,#111,#000)', '#f5c518'),
    'Outros':                  ('linear-gradient(135deg,#4a5568,#2d3748)', '#fff'),
}
_DEFAULT_GRADIENT = ('linear-gradient(135deg,#2d3748,#1a202c)', '#fff')

# ── Ícones por categoria ────────────────────────────────────────────
CATEGORY_ICONS = {
    'Alimentação':  'bi-cart3',
    'Transporte':   'bi-car-front',
    'Saúde':        'bi-heart-pulse',
    'Lazer':        'bi-controller',
    'Moradia':      'bi-house',
    'Educação':     'bi-book',
    'Vestuário':    'bi-bag',
    'Serviços':     'bi-tools',
    'Compras':      'bi-bag-heart',
    'Beleza':       'bi-stars',
    'Internet':     'bi-wifi',
    'Telefone':     'bi-phone',
    'Outros':       'bi-tag',
}

CATEGORY_COLORS = {
    'Alimentação': '#FF6384', 'Beleza': '#f72585', 'Educação': '#FFCE56',
    'Lazer': '#FF9F40',       'Moradia': '#9966FF', 'Saúde': '#4BC0C0',
    'Internet': '#4361ee',    'Telefone': '#43aa8b', 'Transporte': '#36A2EB',
    'Outros': '#C9CBCF',
}


def card_gradient(card: CreditCard) -> tuple[str, str]:
    """Retorna (gradient_css, text_color) para o cartão."""
    return BANK_GRADIENTS.get(card.bank or '', _DEFAULT_GRADIENT)


def invoice_status(card: CreditCard, month: int, year: int) -> str:
    """
    Retorna o status da fatura: 'aberta', 'fechada' ou 'futura'.
    - aberta:  mês atual antes do best_buy_day
    - fechada: mês atual após best_buy_day, ou meses passados
    - futura:  meses futuros
    """
    now = datetime.now()
    cur = (year, month)
    today = (now.year, now.month)

    if cur > today:
        return 'futura'
    if cur == today:
        return 'aberta' if now.day <= card.best_buy_day else 'fechada'
    return 'fechada'


def invoice_total(card_id: int, month: int, year: int,
                  payment_method: str | None = None) -> float:
    """
    Soma despesas do cartão no mês.
    payment_method=None → todas; 'Cartão de Crédito' → só crédito; etc.
    """
    q = (db.session.query(func.sum(Expense.amount))
         .filter(Expense.card_id == card_id,
                 Expense.month == month,
                 Expense.year == year))
    if payment_method:
        q = q.filter(Expense.payment_method == payment_method)
    return float(q.scalar() or 0)


def credit_invoice_total(card_id: int, month: int, year: int) -> float:
    return invoice_total(card_id, month, year, 'Cartão de Crédito')


def debit_total(card_id: int, month: int, year: int) -> float:
    return invoice_total(card_id, month, year, 'Cartão de Débito')


def future_installments_total(card_id: int, month: int, year: int) -> float:
    """Total de parcelas futuras (do mesmo cartão) além do mês atual."""
    total = (db.session.query(func.sum(Expense.amount))
             .filter(
                 Expense.card_id == card_id,
                 or_(
                     Expense.year > year,
                     and_(Expense.year == year, Expense.month > month),
                 )
             ).scalar() or 0)
    return float(total)


def vr_va_balance(card: CreditCard, month: int, year: int) -> dict | None:
    """
    Retorna saldo atual de um cartão VR ou VA.
    Retorna None se o cartão não for VR/VA ou não tiver monthly_amount.
    """
    ct = card.card_type or 'credit'
    if ct not in ('vr', 'va') or not card.monthly_amount:
        return None
    monthly = float(card.monthly_amount)
    spent = float(
        db.session.query(func.sum(Expense.amount))
        .filter(Expense.card_id == card.id,
                Expense.month == month,
                Expense.year == year)
        .scalar() or 0
    )
    remaining = max(monthly - spent, 0)
    pct_used  = min(spent / monthly * 100, 100) if monthly > 0 else 0
    return {
        'monthly':   monthly,
        'spent':     spent,
        'remaining': remaining,
        'pct_used':  round(pct_used, 1),
    }


def get_invoice(card: CreditCard, month: int, year: int) -> dict:
    """
    Retorna estrutura completa de uma fatura de crédito.
    Para cartões que suportam débito também, apenas despesas de crédito entram aqui.
    """
    q = Expense.query.filter(Expense.card_id == card.id,
                             Expense.month == month,
                             Expense.year == year)
    if bool(card.supports_credit):
        q = q.filter(Expense.payment_method == 'Cartão de Crédito')
    expenses = q.order_by(Expense.day, Expense.created_at).all()

    total = sum(float(e.amount) for e in expenses)
    paid_total = sum(float(e.amount) for e in expenses if e.paid)

    # Agrupar por dia
    by_day: dict[int, list] = {}
    for e in expenses:
        by_day.setdefault(e.day, []).append(e)

    # Totais por categoria (para gráfico)
    cat_totals: dict[str, float] = {}
    for e in expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + float(e.amount)

    # Chart JSON
    chart = {
        'labels': list(cat_totals.keys()),
        'data':   list(cat_totals.values()),
        'colors': [CATEGORY_COLORS.get(c, '#C9CBCF') for c in cat_totals],
    } if cat_totals else None

    # Parcelas futuras
    future_total = future_installments_total(card.id, month, year)

    # Meses adjacentes
    prev_m, prev_y = month_offset(month, year, -1)
    next_m, next_y = month_offset(month, year,  1)

    return {
        'expenses':      expenses,
        'by_day':        by_day,
        'total':         total,
        'paid_total':    paid_total,
        'pending_total': total - paid_total,
        'cat_totals':    cat_totals,
        'chart':         chart,
        'future_total':  future_total,
        'status':        invoice_status(card, month, year),
        'prev_month': prev_m, 'prev_year': prev_y,
        'next_month': next_m, 'next_year': next_y,
    }
