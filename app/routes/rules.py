from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app import db
from app.models import CategoryRule
from app.forms import CATEGORIES

rules_bp = Blueprint('rules', __name__, url_prefix='/rules')


def _tenant_id():
    return session.get('tenant_id')


@rules_bp.route('/')
def index():
    tid = _tenant_id()
    rules = (CategoryRule.query
             .filter_by(tenant_id=tid)
             .order_by(CategoryRule.match_count.desc(), CategoryRule.keyword)
             .all())
    return render_template('rules/index.html',
                           rules=rules,
                           categories=sorted(CATEGORIES))


@rules_bp.route('/add', methods=['POST'])
def add():
    tid = _tenant_id()
    keyword  = request.form.get('keyword', '').strip().upper()
    category = request.form.get('category', '').strip()

    if not keyword or not category:
        flash('Palavra-chave e categoria são obrigatórios.', 'danger')
        return redirect(url_for('rules.index'))

    if len(keyword) < 2:
        flash('A palavra-chave deve ter pelo menos 2 caracteres.', 'danger')
        return redirect(url_for('rules.index'))

    existing = CategoryRule.query.filter_by(tenant_id=tid, keyword=keyword).first()
    if existing:
        flash(f'Já existe uma regra para "{keyword}". Edite-a se precisar alterar a categoria.', 'warning')
        return redirect(url_for('rules.index'))

    db.session.add(CategoryRule(tenant_id=tid, keyword=keyword, category=category))
    db.session.commit()
    flash(f'Regra criada: "{keyword}" → {category}', 'success')
    return redirect(url_for('rules.index'))


@rules_bp.route('/edit/<int:rule_id>', methods=['POST'])
def edit(rule_id):
    tid  = _tenant_id()
    rule = CategoryRule.query.filter_by(id=rule_id, tenant_id=tid).first_or_404()

    new_keyword  = request.form.get('keyword', '').strip().upper()
    new_category = request.form.get('category', '').strip()

    if not new_keyword or not new_category:
        flash('Campos obrigatórios não preenchidos.', 'danger')
        return redirect(url_for('rules.index'))

    # Verificar conflito com outra regra (exceto ela própria)
    conflict = (CategoryRule.query
                .filter(CategoryRule.tenant_id == tid,
                        CategoryRule.keyword == new_keyword,
                        CategoryRule.id != rule_id)
                .first())
    if conflict:
        flash(f'Já existe outra regra para "{new_keyword}".', 'warning')
        return redirect(url_for('rules.index'))

    rule.keyword  = new_keyword
    rule.category = new_category
    db.session.commit()
    flash('Regra atualizada com sucesso.', 'success')
    return redirect(url_for('rules.index'))


@rules_bp.route('/delete/<int:rule_id>', methods=['POST'])
def delete(rule_id):
    tid  = _tenant_id()
    rule = CategoryRule.query.filter_by(id=rule_id, tenant_id=tid).first_or_404()
    kw   = rule.keyword
    db.session.delete(rule)
    db.session.commit()
    flash(f'Regra "{kw}" excluída.', 'warning')
    return redirect(url_for('rules.index'))
