"""Seed demo data: organization, entity, COA, demo user, sample transactions."""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from . import db as _db
from .accounting import post_journal
from .models.accounting import Account, AccountType, Journal, JournalLine, JournalSource
from .models.banking import BankAccount, BankTransaction, BankTxStatus
from .models.commerce import Customer, Vendor
from .models.core import Entity, Membership, Organization, Role, User
from .security import hash_password

ZERO = Decimal("0")

CHART = [
    # Assets (1xxx)
    ("1000", "Cash on Hand", AccountType.ASSET, {"is_cash": True}),
    ("1010", "Operating Bank Account", AccountType.ASSET, {"is_bank": True}),
    ("1020", "Savings Account", AccountType.ASSET, {"is_bank": True}),
    ("1100", "Accounts Receivable", AccountType.ASSET, {"is_ar": True}),
    ("1200", "Inventory - Parts", AccountType.ASSET, {}),
    ("1210", "Inventory - Fuel", AccountType.ASSET, {}),
    ("1500", "Equipment", AccountType.ASSET, {}),
    ("1510", "Vehicles", AccountType.ASSET, {}),
    ("1600", "Accumulated Depreciation", AccountType.CONTRA_ASSET, {}),
    # Liabilities (2xxx)
    ("2000", "Accounts Payable", AccountType.LIABILITY, {"is_ap": True}),
    ("2100", "Sales Tax Payable", AccountType.LIABILITY, {}),
    ("2200", "Payroll Liabilities", AccountType.LIABILITY, {}),
    ("2300", "Credit Card Payable", AccountType.LIABILITY, {}),
    ("2500", "Notes Payable", AccountType.LIABILITY, {}),
    # Equity (3xxx)
    ("3000", "Owner Equity", AccountType.EQUITY, {}),
    ("3100", "Retained Earnings", AccountType.EQUITY, {}),
    # Revenue (4xxx)
    ("4000", "Service Revenue", AccountType.REVENUE, {}),
    ("4100", "Parts Revenue", AccountType.REVENUE, {}),
    ("4200", "Fuel Revenue", AccountType.REVENUE, {}),
    ("4300", "Labor Revenue", AccountType.REVENUE, {}),
    ("4900", "Sales Discounts", AccountType.CONTRA_REVENUE, {}),
    # Expenses (5xxx-7xxx)
    ("5000", "COGS - Parts", AccountType.EXPENSE, {}),
    ("5100", "COGS - Fuel", AccountType.EXPENSE, {}),
    ("5200", "COGS - Labor", AccountType.EXPENSE, {}),
    ("6000", "Wages & Salaries", AccountType.EXPENSE, {}),
    ("6010", "Payroll Taxes", AccountType.EXPENSE, {}),
    ("6100", "Rent", AccountType.EXPENSE, {}),
    ("6200", "Utilities", AccountType.EXPENSE, {}),
    ("6300", "Insurance", AccountType.EXPENSE, {}),
    ("6400", "Supplies", AccountType.EXPENSE, {}),
    ("6500", "Repairs & Maintenance", AccountType.EXPENSE, {}),
    ("6600", "Software & Subscriptions", AccountType.EXPENSE, {}),
    ("6700", "Bank Fees", AccountType.EXPENSE, {}),
    ("6800", "Professional Fees", AccountType.EXPENSE, {}),
    ("6900", "Depreciation Expense", AccountType.EXPENSE, {}),
    ("7000", "Other Expenses", AccountType.EXPENSE, {}),
]


def seed() -> None:
    db = _db.SessionLocal()
    try:
        existing = db.query(Organization).filter(Organization.slug == "jrd").one_or_none()
        if existing:
            print(f"[seed] organization 'jrd' already exists ({existing.id}). Skipping.")
            return

        org = Organization(slug="jrd", name="JRD Companies", base_currency="USD")
        db.add(org)
        db.flush()

        # Two entities for consolidation demo
        jrd_auto = Entity(
            org_id=org.id,
            code="JRD-AUTO",
            name="JRD Auto Repair",
            legal_name="JRD Auto Repair, LLC",
            industry="automotive_repair",
            is_consolidation_target=True,
        )
        jrd_fuel = Entity(
            org_id=org.id,
            code="JRD-FUEL",
            name="JRD Fuel Stop",
            legal_name="JRD Fuel Stop, LLC",
            industry="fuel_retail",
            is_consolidation_target=True,
        )
        db.add_all([jrd_auto, jrd_fuel])
        db.flush()

        user = User(
            email="demo@jrdbooks.io",
            full_name="Demo Admin",
            password_hash=hash_password("demo"),
        )
        db.add(user)
        db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role=Role.OWNER))

        accounts_by_entity: dict[str, dict[str, Account]] = {}
        for entity in (jrd_auto, jrd_fuel):
            entity_accounts: dict[str, Account] = {}
            for code, name, type_, flags in CHART:
                acct = Account(
                    org_id=org.id,
                    entity_id=entity.id,
                    code=code,
                    name=name,
                    type=type_,
                    **flags,
                )
                db.add(acct)
                entity_accounts[code] = acct
            accounts_by_entity[entity.code] = entity_accounts
        db.flush()

        # Bank accounts
        for entity, accounts in (
            (jrd_auto, accounts_by_entity["JRD-AUTO"]),
            (jrd_fuel, accounts_by_entity["JRD-FUEL"]),
        ):
            for code, name, balance, mask in [
                ("1010", "Operating Checking", Decimal("48230.55"), "1234"),
                ("1020", "Savings", Decimal("125000.00"), "5678"),
            ]:
                db.add(
                    BankAccount(
                        org_id=org.id,
                        entity_id=entity.id,
                        ledger_account_id=accounts[code].id,
                        name=f"{entity.code} - {name}",
                        institution="Chase",
                        mask=mask,
                        last_balance=balance,
                        provider="seed",
                        external_id=f"{entity.code}-{code}",
                        last_sync_at=datetime.now(timezone.utc),
                    )
                )

        # Customers & vendors (org-wide)
        customers = [
            Customer(
                org_id=org.id,
                code=f"C{i:04d}",
                display_name=name,
                email=f"{slug}@example.com",
                payment_terms_days=30,
            )
            for i, (name, slug) in enumerate(
                [
                    ("Acme Logistics", "acme"),
                    ("Riverside Trucking", "riverside"),
                    ("Northstar Construction", "northstar"),
                    ("Mountain Movers", "mountain"),
                    ("City Couriers", "city"),
                ],
                start=1,
            )
        ]
        db.add_all(customers)
        vendors = [
            Vendor(
                org_id=org.id,
                code=f"V{i:04d}",
                display_name=name,
                email=f"ap@{slug}.example.com",
                default_terms_days=30,
            )
            for i, (name, slug) in enumerate(
                [
                    ("Sunoco Wholesale", "sunoco"),
                    ("NAPA Auto Parts", "napa"),
                    ("AutoZone Pro", "autozone"),
                    ("Acme Tooling", "acmetool"),
                    ("City Utilities", "cityutil"),
                ],
                start=1,
            )
        ]
        db.add_all(vendors)
        db.flush()

        # Opening balance journal for each entity: cash + savings -> owner equity
        for entity_code, accounts in accounts_by_entity.items():
            cash = accounts["1010"]
            savings = accounts["1020"]
            equity = accounts["3000"]
            entity = jrd_auto if entity_code == "JRD-AUTO" else jrd_fuel
            j = Journal(
                org_id=org.id,
                entity_id=entity.id,
                journal_no=f"OB-{entity_code}",
                posting_date=date.today() - timedelta(days=60),
                memo=f"Opening balance for {entity.name}",
                source=JournalSource.SYSTEM,
                currency="USD",
            )
            db.add(j)
            db.flush()
            db.add(
                JournalLine(
                    journal_id=j.id,
                    line_no=1,
                    account_id=cash.id,
                    debit=Decimal("48230.55"),
                    credit=ZERO,
                    description="Opening operating cash",
                )
            )
            db.add(
                JournalLine(
                    journal_id=j.id,
                    line_no=2,
                    account_id=savings.id,
                    debit=Decimal("125000.00"),
                    credit=ZERO,
                    description="Opening savings",
                )
            )
            db.add(
                JournalLine(
                    journal_id=j.id,
                    line_no=3,
                    account_id=equity.id,
                    debit=ZERO,
                    credit=Decimal("173230.55"),
                    description="Owner contribution",
                )
            )
            db.flush()
            db.refresh(j)
            post_journal(db, j.id, actor_user_id=user.id)

        # A handful of revenue & expense journals across the last 60 days
        import random

        random.seed(42)
        today = date.today()
        for entity_code, accounts in accounts_by_entity.items():
            entity = jrd_auto if entity_code == "JRD-AUTO" else jrd_fuel
            bank = accounts["1010"]
            for n in range(30):
                day = today - timedelta(days=random.randint(0, 55))
                is_revenue = random.random() < 0.55
                amt = Decimal(str(round(random.uniform(40, 1800), 2)))
                if is_revenue:
                    rev = accounts["4000"] if entity_code == "JRD-AUTO" else accounts["4200"]
                    j = Journal(
                        org_id=org.id,
                        entity_id=entity.id,
                        journal_no=f"SEED-R-{entity_code}-{n}",
                        posting_date=day,
                        memo=f"Sample sale #{n}",
                        source=JournalSource.SYSTEM,
                    )
                    db.add(j)
                    db.flush()
                    db.add(JournalLine(journal_id=j.id, line_no=1, account_id=bank.id, debit=amt, credit=ZERO))
                    db.add(JournalLine(journal_id=j.id, line_no=2, account_id=rev.id, debit=ZERO, credit=amt))
                    db.flush()
                    db.refresh(j)
                    post_journal(db, j.id, actor_user_id=user.id)
                else:
                    expense_code = random.choice(["6100", "6200", "6400", "6600", "5000"])
                    exp = accounts[expense_code]
                    j = Journal(
                        org_id=org.id,
                        entity_id=entity.id,
                        journal_no=f"SEED-E-{entity_code}-{n}",
                        posting_date=day,
                        memo=f"Sample expense #{n}",
                        source=JournalSource.SYSTEM,
                    )
                    db.add(j)
                    db.flush()
                    db.add(JournalLine(journal_id=j.id, line_no=1, account_id=exp.id, debit=amt, credit=ZERO))
                    db.add(JournalLine(journal_id=j.id, line_no=2, account_id=bank.id, debit=ZERO, credit=amt))
                    db.flush()
                    db.refresh(j)
                    post_journal(db, j.id, actor_user_id=user.id)

        # Some unreconciled bank transactions for the reconciliation queue
        bank_accounts = (
            db.query(BankAccount).filter(BankAccount.org_id == org.id).all()
        )
        for ba in bank_accounts:
            for k in range(8):
                amt = Decimal(str(round(random.uniform(-650, 1200), 2)))
                if amt == 0:
                    continue
                db.add(
                    BankTransaction(
                        org_id=ba.org_id,
                        entity_id=ba.entity_id,
                        bank_account_id=ba.id,
                        external_id=f"{ba.external_id}-feed-{k}",
                        txn_date=today - timedelta(days=k),
                        description=random.choice(
                            [
                                "ACH from Acme Logistics",
                                "Stripe payout",
                                "Square deposit",
                                "Fuel - Sunoco",
                                "NAPA Auto Parts",
                                "Utility bill",
                                "Rent payment",
                                "Insurance premium",
                                "Office supplies",
                                "Card processing fees",
                            ]
                        ),
                        amount=amt,
                        status=BankTxStatus.UNRECONCILED,
                    )
                )

        db.commit()
        print(f"[seed] org={org.slug} id={org.id}")
        print(f"[seed] user={user.email} password=demo")
        print(f"[seed] entities={[e.code for e in (jrd_auto, jrd_fuel)]}")
        print(f"[seed] accounts seeded per entity: {len(CHART)}")
    except IntegrityError as exc:
        db.rollback()
        print(f"[seed] aborted: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
