from datetime import datetime
from app import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)

    salaries = db.relationship('Salary', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    installment_groups = db.relationship('InstallmentGroup', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.name}>'


class Salary(db.Model):
    __tablename__ = 'salaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'year', 'month', name='uq_salary_user_year_month'),
    )

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
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<InstallmentGroup {self.description} {self.num_installments}x>'


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Expense {self.description} R${self.amount} {self.month}/{self.year}>'
