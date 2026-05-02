from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash


class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    telegram_enabled = db.Column(db.Boolean, default=False)
    telegram_token = db.Column(db.Text, nullable=True)
    telegram_chat_id = db.Column(db.Text, nullable=True)
    telegram_hour = db.Column(db.Integer, default=8)
    telegram_minute = db.Column(db.Integer, default=0)
    trial_expires_at = db.Column(db.DateTime, nullable=True)

    users = db.relationship('User', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def trial_active(self):
        if self.trial_expires_at is None:
            return True
        return datetime.utcnow() <= self.trial_expires_at

    @property
    def trial_days_left(self):
        if self.trial_expires_at is None:
            return None
        delta = (self.trial_expires_at - datetime.utcnow()).days
        return max(0, delta)

    def __repr__(self):
        return f'<Tenant {self.name} ({self.code})>'


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=True, unique=True)
    password_hash = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.Text, nullable=True)

    salaries = db.relationship('Salary', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    installment_groups = db.relationship('InstallmentGroup', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    recurring_groups = db.relationship('RecurringGroup', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    investments = db.relationship('Investment', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name}>'


class Salary(db.Model):
    __tablename__ = 'salaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    company = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Salary user={self.user_id} {self.month}/{self.year} R${self.amount}>'


class InstallmentGroup(db.Model):
    __tablename__ = 'installment_groups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    num_installments = db.Column(db.Integer, nullable=False)
    bank = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    installments = db.relationship('Expense', backref='installment_group', lazy='dynamic',
                                   cascade='all, delete-orphan',
                                   foreign_keys='Expense.installment_group_id')

    def __repr__(self):
        return f'<InstallmentGroup {self.description} {self.num_installments}x>'


class RecurringGroup(db.Model):
    __tablename__ = 'recurring_groups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    num_recurrences = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recurrences = db.relationship('Expense', backref='recurring_group', lazy='dynamic',
                                  cascade='all, delete-orphan',
                                  foreign_keys='Expense.recurring_group_id')

    def __repr__(self):
        return f'<RecurringGroup {self.description} {self.num_recurrences}x>'


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.Text, nullable=False)
    bank = db.Column(db.Text, nullable=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    installment_group_id = db.Column(db.Integer, db.ForeignKey('installment_groups.id'), nullable=True)
    installment_number = db.Column(db.Integer, nullable=True)
    recurring_group_id = db.Column(db.Integer, db.ForeignKey('recurring_groups.id'), nullable=True)
    recurring_number = db.Column(db.Integer, nullable=True)
    paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Expense {self.description} R${self.amount} {self.month}/{self.year}>'


class Investment(db.Model):
    __tablename__ = 'investments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    investment_type = db.Column(db.Text, nullable=False)
    annual_rate = db.Column(db.Numeric(6, 2), nullable=False)
    crypto_coin = db.Column(db.Text, nullable=True)
    crypto_buy_price = db.Column(db.Numeric(18, 8), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Investment {self.investment_type} R${self.amount} {self.month}/{self.year}>'
