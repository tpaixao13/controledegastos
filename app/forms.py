from flask_wtf import FlaskForm
from wtforms import (StringField, DecimalField, SelectField, IntegerField,
                     BooleanField, RadioField, SubmitField)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

CATEGORIES = [
    ('Alimentação', 'Alimentação'),
    ('Transporte', 'Transporte'),
    ('Educação', 'Educação'),
    ('Saúde', 'Saúde'),
    ('Moradia', 'Moradia'),
    ('Lazer', 'Lazer'),
    ('Outros', 'Outros'),
]

PAYMENT_METHODS = [
    ('PIX', 'PIX'),
    ('Cartão de Débito', 'Cartão de Débito'),
    ('Cartão de Crédito', 'Cartão de Crédito'),
    ('Dinheiro', 'Dinheiro'),
]

BANKS = [
    ('', '— Selecione o banco —'),
    ('Nubank', 'Nubank'),
    ('Itaú', 'Itaú'),
    ('Bradesco', 'Bradesco'),
    ('Banco do Brasil', 'Banco do Brasil'),
    ('Caixa Econômica Federal', 'Caixa Econômica Federal'),
    ('Santander', 'Santander'),
    ('Inter', 'Inter'),
    ('C6 Bank', 'C6 Bank'),
    ('BTG Pactual', 'BTG Pactual'),
    ('Sicredi', 'Sicredi'),
    ('Sicoob', 'Sicoob'),
    ('Safra', 'Safra'),
    ('Original', 'Original'),
    ('Neon', 'Neon'),
    ('PicPay', 'PicPay'),
    ('XP Investimentos', 'XP Investimentos'),
    ('Outros', 'Outros'),
]

MONTHS = [
    (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
    (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
    (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro'),
]

INSTALLMENTS = [(i, f'{i}x') for i in range(2, 13)]


class ExpenseForm(FlaskForm):
    user_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    description = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    amount = DecimalField('Valor Total (R$)', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    category = SelectField('Categoria', choices=CATEGORIES, validators=[DataRequired()])
    payment_method = SelectField('Forma de Pagamento', choices=PAYMENT_METHODS, validators=[DataRequired()])
    bank = SelectField('Banco / Cartão', choices=BANKS, validators=[Optional()])
    credit_type = RadioField('Tipo', choices=[('avista', 'À vista'), ('parcelado', 'Parcelado')],
                             default='avista', validators=[Optional()])
    num_installments = SelectField('Nº de Parcelas', choices=INSTALLMENTS, coerce=int, validators=[Optional()])
    year = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    month = SelectField('Mês', choices=MONTHS, coerce=int, validators=[DataRequired()])
    day = IntegerField('Dia', validators=[DataRequired(), NumberRange(min=1, max=31)])
    submit = SubmitField('Salvar')


class SalaryForm(FlaskForm):
    user_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    year = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    month = SelectField('Mês', choices=MONTHS, coerce=int, validators=[DataRequired()])
    amount = DecimalField('Salário (R$)', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Salvar Salário')
