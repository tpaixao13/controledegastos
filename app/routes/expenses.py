import csv
import io
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from app import db
from app.models import User, Expense, InstallmentGroup, RecurringGroup
from app.forms import ExpenseForm
from app.utils import tenant_users, tenant_user_ids, MONTH_NAMES_SHORT, month_offset
from datetime import datetime

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

ITEMS_PER_PAGE = 20

CATEGORIES = [
    'Alimentação', 'Transporte', 'Saúde', 'Lazer', 'Moradia',
    'Educação', 'Vestuário', 'Serviços', 'Compras', 'Outros',
]


@expenses_bp.route('/')
def list():
    users = tenant_users().order_by(User.name).all()
    uids = [u.id for u in users]
    now = datetime.now()

    user_id = request.args.get('user_id', type=int)
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)
    if not 0 <= month <= 12:  # 0 = todos os meses
        month = now.month
    if not 2000 <= year <= 2100:
        year = now.year
    category = request.args.get('category', '')
    payment_method = request.args.get('payment_method', '')
    page = request.args.get('page', 1, type=int)

    # month=0 significa "todos os meses"
    query = Expense.query.filter(Expense.user_id.in_(uids)).filter(Expense.year == year)
    if month != 0:
        query = query.filter(Expense.month == month)
    if user_id and user_id in uids:
        query = query.filter(Expense.user_id == user_id)
    if category:
        query = query.filter(Expense.category == category)
    if payment_method:
        query = query.filter(Expense.payment_method == payment_method)

    query = query.order_by(Expense.month.desc(), Expense.day.desc(), Expense.created_at.desc())
    pagination = query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    expenses = pagination.items

    total_mes = sum(float(e.amount) for e in query.all())

    categories = (db.session.query(Expense.category)
                  .filter(Expense.user_id.in_(uids))
                  .distinct().order_by(Expense.category).all())
    categories = [c[0] for c in categories]

    payment_methods = ['PIX', 'Cartão de Débito', 'Cartão de Crédito', 'Dinheiro']

    return render_template('expenses/list.html',
                           expenses=expenses,
                           pagination=pagination,
                           users=users,
                           categories=categories,
                           payment_methods=payment_methods,
                           total_mes=total_mes,
                           today=now.date(),
                           filters={'user_id': user_id, 'month': month, 'year': year,
                                    'category': category, 'payment_method': payment_method})


@expenses_bp.route('/export')
def export_csv():
    now = datetime.now()
    uids = tenant_user_ids()
    user_id = request.args.get('user_id', type=int)
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)
    category = request.args.get('category', '')

    query = Expense.query.filter(Expense.user_id.in_(uids), Expense.year == year, Expense.month == month)
    if user_id and user_id in uids:
        query = query.filter(Expense.user_id == user_id)
    if category:
        query = query.filter(Expense.category == category)
    query = query.order_by(Expense.day.asc(), Expense.created_at.asc())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Pessoa', 'Dia', 'Mês', 'Ano', 'Descrição', 'Categoria',
                     'Forma de Pagamento', 'Banco', 'Valor (R$)', 'Parcela', 'Recorrente'])

    for e in query.all():
        parcela = ''
        if e.installment_group_id:
            parcela = f'{e.installment_number}/{e.installment_group.num_installments}'
        elif e.recurring_group_id:
            parcela = f'Recorrente {e.recurring_number}/{e.recurring_group.num_recurrences}'

        writer.writerow([
            e.user.name,
            e.day,
            e.month,
            e.year,
            e.description,
            e.category,
            e.payment_method,
            e.bank or '',
            f'{float(e.amount):.2f}'.replace('.', ','),
            parcela,
            'Sim' if e.recurring_group_id else 'Não',
        ])

    output.seek(0)
    filename = f'despesas_{year}_{month:02d}.csv'
    return Response(
        '\ufeff' + output.getvalue(),  # BOM para Excel reconhecer UTF-8
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@expenses_bp.route('/add', methods=['GET', 'POST'])
def add():
    users = tenant_users().order_by(User.name).all()
    form = ExpenseForm()
    form.user_id.choices = [(u.id, u.name) for u in users]

    now = datetime.now()
    if request.method == 'GET':
        form.year.data = now.year
        form.month.data = now.month
        form.day.data = now.day
        form.num_installments.data = 2
        form.recurring_times.data = 2

    if form.validate_on_submit():
        payment = form.payment_method.data
        bank = form.bank.data if payment in ('Cartão de Débito', 'Cartão de Crédito') else None

        is_parcelado = (payment == 'Cartão de Crédito' and
                        form.credit_type.data == 'parcelado')
        is_recurring = form.is_recurring.data

        if is_parcelado:
            _create_installments(form, bank)
        elif is_recurring:
            _create_recurring(form, bank, payment)
        else:
            expense = Expense(
                user_id=form.user_id.data,
                description=form.description.data,
                amount=form.amount.data,
                category=form.category.data,
                payment_method=payment,
                bank=bank,
                year=form.year.data,
                month=form.month.data,
                day=form.day.data,
            )
            db.session.add(expense)
            db.session.commit()
            flash('Despesa adicionada com sucesso!', 'success')

        return redirect(url_for('expenses.list'))

    return render_template('expenses/add.html', form=form, users=users)


@expenses_bp.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit(expense_id):
    uids = tenant_user_ids()
    expense = Expense.query.filter(Expense.id == expense_id, Expense.user_id.in_(uids)).first_or_404()
    users = tenant_users().order_by(User.name).all()
    form = ExpenseForm(obj=expense)
    form.user_id.choices = [(u.id, u.name) for u in users]

    if request.method == 'GET':
        form.credit_type.data = 'avista'

    if form.validate_on_submit():
        payment = form.payment_method.data
        expense.user_id = form.user_id.data
        expense.description = form.description.data
        expense.amount = form.amount.data
        expense.category = form.category.data
        expense.payment_method = payment
        expense.bank = form.bank.data if payment in ('Cartão de Débito', 'Cartão de Crédito') else None
        expense.year = form.year.data
        expense.month = form.month.data
        expense.day = form.day.data
        expense.paid = form.paid.data
        db.session.commit()
        flash('Despesa atualizada com sucesso!', 'success')
        return redirect(url_for('expenses.list'))

    return render_template('expenses/edit.html', form=form, expense=expense, users=users)


@expenses_bp.route('/delete/<int:expense_id>', methods=['POST'])
def delete(expense_id):
    uids = tenant_user_ids()
    expense = Expense.query.filter(Expense.id == expense_id, Expense.user_id.in_(uids)).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    flash('Despesa eliminada.', 'warning')
    return redirect(url_for('expenses.list'))


@expenses_bp.route('/delete-group/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    uids = tenant_user_ids()
    group = InstallmentGroup.query.filter(InstallmentGroup.id == group_id, InstallmentGroup.user_id.in_(uids)).first_or_404()
    count = group.installments.count()
    db.session.delete(group)
    db.session.commit()
    flash(f'Todas as {count} parcelas foram eliminadas.', 'warning')
    return redirect(url_for('expenses.list'))


@expenses_bp.route('/toggle-paid/<int:expense_id>', methods=['POST'])
def toggle_paid(expense_id):
    uids = tenant_user_ids()
    expense = Expense.query.filter(Expense.id == expense_id, Expense.user_id.in_(uids)).first_or_404()
    expense.paid = not bool(expense.paid)
    db.session.commit()
    next_url = request.form.get('next') or ''
    if not next_url or urlparse(next_url).netloc:
        next_url = url_for('expenses.list')
    return redirect(next_url)


@expenses_bp.route('/delete-recurring/<int:group_id>', methods=['POST'])
def delete_recurring(group_id):
    uids = tenant_user_ids()
    group = RecurringGroup.query.filter(RecurringGroup.id == group_id, RecurringGroup.user_id.in_(uids)).first_or_404()
    count = group.recurrences.count()
    db.session.delete(group)
    db.session.commit()
    flash(f'Todas as {count} recorrências foram eliminadas.', 'warning')
    return redirect(url_for('expenses.list'))


@expenses_bp.route('/import-c6', methods=['GET'])
def import_c6():
    users = tenant_users().order_by(User.name).all()
    return render_template('expenses/import_c6_upload.html', users=users)


@expenses_bp.route('/import-c6/parse', methods=['POST'])
def import_c6_parse():
    from app.importers.c6 import parse_c6_pdf

    users = tenant_users().order_by(User.name).all()
    uids = [u.id for u in users]

    user_id = request.form.get('user_id', type=int)
    if not user_id or user_id not in uids:
        flash('Selecione um usuário válido.', 'danger')
        return redirect(url_for('expenses.import_c6'))

    pdf_file = request.files.get('pdf_file')
    if not pdf_file or not pdf_file.filename.lower().endswith('.pdf'):
        flash('Selecione um arquivo PDF válido.', 'danger')
        return redirect(url_for('expenses.import_c6'))

    pdf_bytes = pdf_file.read()
    try:
        transactions = parse_c6_pdf(pdf_bytes)
    except Exception:
        flash('Erro ao processar o PDF. Verifique se é um extrato C6 válido.', 'danger')
        return redirect(url_for('expenses.import_c6'))

    if not transactions:
        flash('Nenhuma transação encontrada no PDF. Verifique se é um extrato C6 válido.', 'warning')
        return redirect(url_for('expenses.import_c6'))

    selected_user = next(u for u in users if u.id == user_id)
    return render_template(
        'expenses/import_c6_preview.html',
        transactions=transactions,
        users=users,
        selected_user=selected_user,
        user_id=user_id,
        categories=CATEGORIES,
        total=sum(t.amount for t in transactions),
    )


@expenses_bp.route('/import-c6/confirm', methods=['POST'])
def import_c6_confirm():
    uids = tenant_user_ids()
    indices = request.form.getlist('idx')
    count = 0

    for idx in indices:
        if not request.form.get(f'include_{idx}'):
            continue
        try:
            user_id = int(request.form[f'user_id_{idx}'])
            if user_id not in uids:
                continue
            day = int(request.form[f'day_{idx}'])
            month = int(request.form[f'month_{idx}'])
            year = int(request.form[f'year_{idx}'])
            description = request.form[f'desc_{idx}'].strip()
            amount_raw = request.form[f'amount_{idx}'].replace(',', '.')
            amount = float(amount_raw)
            category = request.form.get(f'category_{idx}', 'Outros')
        except (KeyError, ValueError):
            continue

        if not description or amount <= 0:
            continue

        expense = Expense(
            user_id=user_id,
            description=description,
            amount=amount,
            category=category,
            payment_method='Cartão de Crédito',
            bank='C6',
            year=year,
            month=month,
            day=day,
        )
        db.session.add(expense)
        count += 1

    db.session.commit()
    flash(f'{count} despesa(s) importada(s) com sucesso!', 'success')
    return redirect(url_for('expenses.list'))


def _create_installments(form, bank):
    n = form.num_installments.data
    total = Decimal(str(form.amount.data))
    parcela = (total / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    ultima_parcela = total - parcela * (n - 1)

    group = InstallmentGroup(
        user_id=form.user_id.data,
        description=form.description.data,
        total_amount=total,
        num_installments=n,
        bank=bank or '',
    )
    db.session.add(group)
    db.session.flush()

    mes_inicio = form.month.data
    ano_inicio = form.year.data

    for i in range(n):
        mes_atual, ano_atual = month_offset(mes_inicio, ano_inicio, i)
        valor = ultima_parcela if i == n - 1 else parcela

        expense = Expense(
            user_id=form.user_id.data,
            description=form.description.data,
            amount=valor,
            category=form.category.data,
            payment_method='Cartão de Crédito',
            bank=bank,
            year=ano_atual,
            month=mes_atual,
            day=form.day.data,
            installment_group_id=group.id,
            installment_number=i + 1,
        )
        db.session.add(expense)

    db.session.commit()

    mes_fim, ano_fim = month_offset(mes_inicio, ano_inicio, n - 1)
    parcela_fmt = f'R$ {float(parcela):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    flash(
        f'{n} parcelas criadas de {parcela_fmt} cada '
        f'({MONTH_NAMES_SHORT[mes_inicio-1]}/{ano_inicio} → {MONTH_NAMES_SHORT[mes_fim-1]}/{ano_fim})',
        'success'
    )


def _create_recurring(form, bank, payment):
    n = form.recurring_times.data
    amount = Decimal(str(form.amount.data))

    group = RecurringGroup(
        user_id=form.user_id.data,
        description=form.description.data,
        amount=amount,
        num_recurrences=n,
    )
    db.session.add(group)
    db.session.flush()

    mes_inicio = form.month.data
    ano_inicio = form.year.data

    for i in range(n):
        mes_atual, ano_atual = month_offset(mes_inicio, ano_inicio, i)

        expense = Expense(
            user_id=form.user_id.data,
            description=form.description.data,
            amount=amount,
            category=form.category.data,
            payment_method=payment,
            bank=bank,
            year=ano_atual,
            month=mes_atual,
            day=form.day.data,
            recurring_group_id=group.id,
            recurring_number=i + 1,
        )
        db.session.add(expense)

    db.session.commit()

    mes_fim, ano_fim = month_offset(mes_inicio, ano_inicio, n - 1)
    flash(
        f'Despesa recorrente criada por {n} meses '
        f'({MONTH_NAMES_SHORT[mes_inicio-1]}/{ano_inicio} → {MONTH_NAMES_SHORT[mes_fim-1]}/{ano_fim})',
        'success'
    )
