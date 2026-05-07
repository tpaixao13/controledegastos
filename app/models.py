from datetime import datetime, date as _date, timedelta
from app import db
from werkzeug.security import generate_password_hash, check_password_hash


def _easter(year: int) -> _date:
    """Calcula a data da Páscoa (algoritmo de Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return _date(year, month, day)


def _br_holidays(year: int) -> set:
    """Retorna conjunto com feriados nacionais brasileiros do ano (fixos + móveis)."""
    easter = _easter(year)
    holidays = {
        _date(year, 1, 1),               # Confraternização Universal
        _date(year, 4, 21),              # Tiradentes
        _date(year, 5, 1),               # Dia do Trabalho
        _date(year, 9, 7),               # Independência do Brasil
        _date(year, 10, 12),             # N.S. Aparecida
        _date(year, 11, 2),              # Finados
        _date(year, 11, 15),             # Proclamação da República
        _date(year, 12, 25),             # Natal
        easter - timedelta(days=48),     # Carnaval (segunda-feira)
        easter - timedelta(days=47),     # Carnaval (terça-feira)
        easter - timedelta(days=2),      # Sexta-feira Santa
        easter + timedelta(days=60),     # Corpus Christi
    }
    if year >= 2024:
        holidays.add(_date(year, 11, 20))  # Consciência Negra (Lei 14.759/2023)
    return holidays


PLAN_LIMITS = {
    'trial':     1,
    'mensal':    1,
    'anual':     2,
    'vitalicio': 4,
}

PLAN_LABELS = {
    'trial':    'Trial',
    'mensal':   'Mensal',
    'anual':    'Anual',
    'vitalicio': 'Vitalício',
}


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
    telegram_last_sent = db.Column(db.Date, nullable=True)
    trial_expires_at = db.Column(db.DateTime, nullable=True)
    plan = db.Column(db.Text, default='trial', nullable=False)
    extra_members = db.Column(db.Integer, default=0, nullable=False)

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

    @property
    def member_limit(self):
        return PLAN_LIMITS.get(self.plan or 'trial', 2)

    @property
    def plan_label(self):
        return PLAN_LABELS.get(self.plan or 'trial', 'Trial')

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
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)

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


class SalaryGroup(db.Model):
    __tablename__ = 'salary_groups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    salaries = db.relationship('Salary', backref='salary_group', lazy='dynamic',
                               foreign_keys='Salary.salary_group_id')

    def __repr__(self):
        return f'<SalaryGroup user={self.user_id}>'


class Salary(db.Model):
    __tablename__ = 'salaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    salary_group_id = db.Column(db.Integer, db.ForeignKey('salary_groups.id'), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    company = db.Column(db.Text, nullable=True)
    income_type = db.Column(db.Text, nullable=False, default='fixa')
    payment_day = db.Column(db.Integer, nullable=True)
    payment_day_type = db.Column(db.Text, nullable=True)  # 'fixo' or 'util'
    received = db.Column(db.Boolean, default=True)

    def expected_payment_date(self):
        """Returns the expected payment date, skipping weekends and Brazilian national holidays."""
        if not self.payment_day or not self.payment_day_type:
            return None
        import calendar
        if self.payment_day_type == 'util':
            holidays = _br_holidays(self.year)
            count = 0
            for d in range(1, calendar.monthrange(self.year, self.month)[1] + 1):
                dt = _date(self.year, self.month, d)
                if dt.weekday() < 5 and dt not in holidays:
                    count += 1
                    if count == self.payment_day:
                        return dt
            return None
        else:
            max_day = calendar.monthrange(self.year, self.month)[1]
            return _date(self.year, self.month, min(self.payment_day, max_day))

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
