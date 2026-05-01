from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, DecimalField, SelectField, IntegerField,
                     BooleanField, RadioField, SubmitField, PasswordField, HiddenField)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError, EqualTo, Email

CATEGORIES = [
    ('Alimentação', 'Alimentação'),
    ('Beleza', 'Beleza'),
    ('Educação', 'Educação'),
    ('Lazer', 'Lazer'),
    ('Moradia', 'Moradia'),
    ('Saúde', 'Saúde'),
    ('Internet', 'Internet'),
    ('Telefone', 'Telefone'),
    ('Transporte', 'Transporte'),
    ('Outros', 'Outros'),
]

PAYMENT_METHODS = [
    ('', '— Forma de pagamento —'),
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
RECURRENCES = [(i, f'{i}x') for i in range(2, 25)]

CRYPTO_COINS = [
    ('', '— Selecione a moeda —'),
    ('bitcoin', 'Bitcoin (BTC)'),
    ('ethereum', 'Ethereum (ETH)'),
    ('binancecoin', 'BNB (BNB)'),
    ('solana', 'Solana (SOL)'),
    ('ripple', 'XRP (XRP)'),
    ('cardano', 'Cardano (ADA)'),
    ('dogecoin', 'Dogecoin (DOGE)'),
    ('polkadot', 'Polkadot (DOT)'),
    ('avalanche-2', 'Avalanche (AVAX)'),
    ('chainlink', 'Chainlink (LINK)'),
    ('litecoin', 'Litecoin (LTC)'),
    ('matic-network', 'Polygon (MATIC)'),
]

INVESTMENT_TYPES = [
    ('', '— Selecione o tipo —'),
    ('Tesouro Selic', 'Tesouro Selic'),
    ('Tesouro IPCA+', 'Tesouro IPCA+'),
    ('Tesouro Prefixado', 'Tesouro Prefixado'),
    ('CDB', 'CDB'),
    ('LCI', 'LCI'),
    ('LCA', 'LCA'),
    ('CRI/CRA', 'CRI/CRA'),
    ('Poupança', 'Poupança'),
    ('Fundo de Renda Fixa', 'Fundo de Renda Fixa'),
    ('Fundo Multimercado', 'Fundo Multimercado'),
    ('Ações', 'Ações'),
    ('FIIs', 'FIIs (Fundos Imobiliários)'),
    ('Debêntures', 'Debêntures'),
    ('COE', 'COE'),
    ('Criptomoedas', 'Criptomoedas'),
    ('Outros', 'Outros'),
]


def validate_payment_method(form, field):
    if not field.data:
        raise ValidationError('Selecione a forma de pagamento.')


class ExpenseForm(FlaskForm):
    user_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    description = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    amount = DecimalField('Valor Total (R$)', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    category = StringField('Categoria', validators=[DataRequired(), Length(max=50)])
    payment_method = SelectField('Forma de Pagamento', choices=PAYMENT_METHODS,
                                  validators=[validate_payment_method])
    bank = SelectField('Banco / Cartão', choices=BANKS, validators=[Optional()])
    credit_type = RadioField('Tipo', choices=[('avista', 'À vista'), ('parcelado', 'Parcelado')],
                             default='avista', validators=[Optional()])
    num_installments = SelectField('Nº de Parcelas', choices=INSTALLMENTS, coerce=int, validators=[Optional()])
    paid = BooleanField('Marcar como Pago', validators=[Optional()])
    is_recurring = BooleanField('Despesa Recorrente?', validators=[Optional()])
    recurring_times = SelectField('Repetir por quantos meses', choices=RECURRENCES, coerce=int,
                                   validators=[Optional()])
    year = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    month = SelectField('Mês', choices=MONTHS, coerce=int, validators=[DataRequired()])
    day = IntegerField('Dia', validators=[DataRequired(), NumberRange(min=1, max=31)])
    submit = SubmitField('Salvar')


class SalaryForm(FlaskForm):
    user_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    year = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    month = SelectField('Mês', choices=MONTHS, coerce=int, validators=[DataRequired()])
    amount = DecimalField('Salário (R$)', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    company = StringField('Empresa / Fonte', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Adicionar Salário')


class InvestmentForm(FlaskForm):
    user_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    description = StringField('Descrição / Nome', validators=[Optional(), Length(max=200)])
    amount = DecimalField('Valor Investido (R$)', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    investment_type = SelectField('Tipo de Investimento', choices=INVESTMENT_TYPES,
                                   validators=[DataRequired()])
    crypto_coin = SelectField('Criptomoeda', choices=CRYPTO_COINS, validators=[Optional()])
    crypto_buy_price = HiddenField('Preço de Compra')
    annual_rate = DecimalField('Taxa a.a. (%)', places=2,
                                validators=[Optional(), NumberRange(min=0, max=999)],
                                default=0)
    year = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    month = SelectField('Mês', choices=MONTHS, coerce=int, validators=[DataRequired()])
    submit = SubmitField('Registrar Investimento')


class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')


class RegisterTenantForm(FlaskForm):
    user_name = StringField('Seu Nome', validators=[DataRequired(), Length(2, 30)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirmar Senha', validators=[
        DataRequired(), EqualTo('password', message='As senhas não coincidem.')
    ])
    submit = SubmitField('Criar Conta')


class AddMemberForm(FlaskForm):
    user_name = StringField('Nome', validators=[DataRequired(), Length(2, 30)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirmar Senha', validators=[
        DataRequired(), EqualTo('password', message='As senhas não coincidem.')
    ])
    submit_member = SubmitField('Adicionar Membro')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Senha Atual', validators=[DataRequired()])
    new_password = PasswordField('Nova Senha', validators=[
        DataRequired(), Length(min=8, message='Mínimo de 8 caracteres.')
    ])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[
        DataRequired(), EqualTo('new_password', message='As senhas não coincidem.')
    ])
    submit_pwd = SubmitField('Alterar Senha')


class AvatarForm(FlaskForm):
    avatar = FileField('Foto de Perfil', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Apenas imagens (jpg, png, gif, webp).')
    ])
    submit_avatar = SubmitField('Salvar Foto')


class TelegramConfigForm(FlaskForm):
    telegram_enabled = BooleanField('Ativar notificações diárias via Telegram')
    telegram_token = StringField('Token do Bot', validators=[Optional(), Length(max=200)])
    telegram_chat_id = StringField('Chat ID', validators=[Optional(), Length(max=100)])
    telegram_hour = SelectField('Hora', choices=[(i, f'{i:02d}h') for i in range(24)], coerce=int)
    telegram_minute = SelectField('Minuto', choices=[(i, f'{i:02d}') for i in range(0, 60, 5)], coerce=int)
    submit = SubmitField('Salvar Configurações')
