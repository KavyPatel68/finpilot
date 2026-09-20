import random
import os
import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from app.database import get_session_factory, init_db
import app.models  # registers all models on Base.metadata  # noqa: F401
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionDirection, CategorySource
from app.models.budget import Budget
from app.models.goal import Goal, GoalType
from app.services.categorization.taxonomy import CATEGORIES

def seed_data():
    random.seed(42)
    init_db()  # create tables (idempotent)
    SessionLocal = get_session_factory()
    db = SessionLocal()

    # Wipe existing seed data so re-runs are idempotent
    db.query(Transaction).filter(Transaction.user_id == 1).delete(synchronize_session="fetch")
    db.commit()

    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, email="test@example.com", display_name="Demo User", currency="INR")
        db.add(user)
        db.commit()

    savings = db.query(Account).filter(Account.name == "HDFC Savings").first()
    if not savings:
        savings = Account(user_id=1, name="HDFC Savings", type=AccountType.bank, currency="INR")
        db.add(savings)

    cc = db.query(Account).filter(Account.name == "HDFC Credit Card").first()
    if not cc:
        cc = Account(user_id=1, name="HDFC Credit Card", type=AccountType.card, currency="INR")
        db.add(cc)

    db.commit()

    start_date = date(2024, 4, 1)
    months = [start_date + relativedelta(months=i) for i in range(6)]

    transactions_to_add = []

    def add_txn(acc_id, d, desc, amount_minor, direction, cat, subcat=None, is_transfer=False):
        transactions_to_add.append(
            Transaction(
                user_id=1, account_id=acc_id, date=d, raw_description=desc,
                amount_minor=amount_minor, direction=direction, category=cat,
                subcategory=subcat, category_source=CategorySource.rule,
                is_transfer=is_transfer
            )
        )

    for i, m in enumerate(months):
        # Salary
        add_txn(savings.id, date(m.year, m.month, 1), "NEFT CR-SALARY CREDIT", 8500000, TransactionDirection.income, "Income")
        # Rent
        add_txn(savings.id, date(m.year, m.month, 5), "IMPS/123456789/Rent Payment", 2200000, TransactionDirection.expense, "Housing/Rent")
        # EMI
        add_txn(savings.id, date(m.year, m.month, 7), "Home Loan EMI", 1250000, TransactionDirection.expense, "EMI/Loans")

        # Netflix — price hike in Aug 2024
        netflix_amt = 79900 if m >= date(2024, 8, 1) else 64900
        add_txn(cc.id, date(m.year, m.month, 10), "Netflix", netflix_amt, TransactionDirection.expense, "Subscriptions")
        if m == date(2024, 6, 1):
            # Duplicate charge: same amount, same day, different bank reference in narration
            # (real duplicates always have distinct bank reference IDs)
            add_txn(cc.id, date(2024, 6, 10), "Netflix REF#DUP987654", 64900, TransactionDirection.expense, "Subscriptions")

        # Spotify
        add_txn(cc.id, date(m.year, m.month, 15), "Spotify", 11900, TransactionDirection.expense, "Subscriptions")

        # Prime
        if i in [0, 3]: # Apr, Jul
            add_txn(cc.id, date(m.year, m.month, 18), "Amazon Prime", 149900, TransactionDirection.expense, "Subscriptions")
            
        # Electricity
        add_txn(cc.id, date(m.year, m.month, 20), "BESCOM Electricity", random.randint(1800, 3500) * 100, TransactionDirection.expense, "Utilities")
        
        # Groceries
        for _ in range(3):
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), random.choice(["Blinkit", "BigBasket", "Zepto"]), random.randint(200, 2500) * 100, TransactionDirection.expense, "Groceries")
            
        # Dining
        for _ in range(4):
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), random.choice(["Zomato", "Swiggy", "UPI/DR/12345/Swiggy"]), random.randint(150, 2000) * 100, TransactionDirection.expense, "Dining")

        # Transport
        for _ in range(6):
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), random.choice(["Ola", "Uber"]), random.randint(80, 600) * 100, TransactionDirection.expense, "Transport")

        # Fuel
        add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), "HPCL Petrol Pump", random.randint(3000, 5000) * 100, TransactionDirection.expense, "Fuel")
        
        # ATM
        add_txn(savings.id, date(m.year, m.month, random.randint(1, 28)), "ATM Cash Withdrawal", random.randint(5000, 10000) * 100, TransactionDirection.expense, "Other")
        
        # Transfer
        d_trans = date(m.year, m.month, 25)
        add_txn(savings.id, d_trans, "Transfer to CC", 1000000, TransactionDirection.expense, "Transfers", is_transfer=True)
        add_txn(cc.id, d_trans, "Payment Received", 1000000, TransactionDirection.income, "Transfers", is_transfer=True)

        # Ambiguous
        if m == date(2024, 5, 1):
            add_txn(savings.id, date(m.year, m.month, 12), "NEFT CR-GARG ENT 12345", 500000, TransactionDirection.income, "Other")
            
        # Refund
        if m == date(2024, 8, 1):
            add_txn(cc.id, date(m.year, m.month, 22), "Amazon Refund", 120000, TransactionDirection.income, "Shopping", subcat="Refund")

        # Shopping
        if m == date(2024, 7, 1): # spike
            add_txn(cc.id, date(m.year, m.month, 14), "Amazon", 2500000, TransactionDirection.expense, "Shopping")
            add_txn(cc.id, date(m.year, m.month, 16), "Myntra", 1000000, TransactionDirection.expense, "Shopping")
        else:
            add_txn(cc.id, date(m.year, m.month, random.randint(1, 28)), "Amazon", random.randint(2000, 5000) * 100, TransactionDirection.expense, "Shopping")

    # Messy rows
    add_txn(savings.id, date(2024, 4, 10), "UPI/CR/98765/SALARY", 150000, TransactionDirection.income, "Income")
    add_txn(savings.id, date(2024, 4, 15), "Paid 1,500.00 to vendor", 150000, TransactionDirection.expense, "Other")

    for t in transactions_to_add:
        db.add(t)

    # Seed Budgets for demo
    db.query(Budget).filter(Budget.user_id == 1).delete(synchronize_session="fetch")
    db.add(Budget(user_id=1, category="Dining", monthly_limit_minor=1000000, effective_from=date(2024, 4, 1)))  # ₹10,000
    db.add(Budget(user_id=1, category="Groceries", monthly_limit_minor=1500000, effective_from=date(2024, 4, 1)))  # ₹15,000
    db.add(Budget(user_id=1, category="Shopping", monthly_limit_minor=800000, effective_from=date(2024, 4, 1)))  # ₹8,000

    # Seed Goals for demo
    db.query(Goal).filter(Goal.user_id == 1).delete(synchronize_session="fetch")
    today = date.today()
    db.add(Goal(
        user_id=1,
        name="Emergency Fund",
        type=GoalType.emergency_fund,
        target_amount_minor=30000000,  # ₹300,000
        current_amount_minor=12000000,  # ₹120,000 (40%)
        target_date=today + relativedelta(months=12),
        monthly_contribution_planned_minor=1500000,  # ₹15,000
        is_active=True,
    ))
    db.add(Goal(
        user_id=1,
        name="Goa Holiday",
        type=GoalType.purchase,
        target_amount_minor=5000000,  # ₹50,000
        current_amount_minor=3500000,  # ₹35,000 (70%)
        target_date=today + relativedelta(months=4),
        monthly_contribution_planned_minor=500000,  # ₹5,000
        is_active=True,
    ))

    db.commit()
    print(f"Seeded {len(transactions_to_add)} transactions across {len(months)} months, plus budgets and goals for user_id=1")
    db.close()

if __name__ == "__main__":
    seed_data()
