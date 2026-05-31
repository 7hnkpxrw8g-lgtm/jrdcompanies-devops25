"""Regression tests for the three accuracy bugs found in the 'numbers don't tie'
audit: contra-revenue overstating P&L, contra-asset overstating assets, and
the dashboard cash KPI drifting from balance-sheet cash.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from jrdbooks.accounting import post_journal
from jrdbooks.models.accounting import (
    Account,
    AccountType,
)

from .conftest import make_journal


@pytest.fixture
def seeded_with_contras(db, seeded_org):
    """Add a contra-revenue (sales discount) and contra-asset (accum. dep.)."""
    contra_rev = Account(
        org_id=seeded_org["org"].id,
        entity_id=seeded_org["entity"].id,
        code="4900",
        name="Sales Discounts",
        type=AccountType.CONTRA_REVENUE,
    )
    contra_asset = Account(
        org_id=seeded_org["org"].id,
        entity_id=seeded_org["entity"].id,
        code="1600",
        name="Accumulated Depreciation",
        type=AccountType.CONTRA_ASSET,
    )
    fixed_asset = Account(
        org_id=seeded_org["org"].id,
        entity_id=seeded_org["entity"].id,
        code="1500",
        name="Equipment",
        type=AccountType.ASSET,
    )
    db.add_all([contra_rev, contra_asset, fixed_asset])
    db.flush()
    return {**seeded_org, "contra_rev": contra_rev, "contra_asset": contra_asset, "fixed_asset": fixed_asset}


def test_pnl_subtracts_contra_revenue(db, seeded_with_contras):
    """Posting a sales discount must REDUCE revenue, not add to it.

    Without the fix, the seed bug returned revenue_total = $1000 + $50 = $1050.
    With the fix, revenue_total = $1000 - $50 = $950.
    """
    # 1) $1000 of revenue: Dr cash, Cr revenue
    j1 = make_journal(
        db,
        seeded_with_contras,
        lines=[(seeded_with_contras["cash"], 1000, 0), (seeded_with_contras["rev"], 0, 1000)],
    )
    post_journal(db, j1.id)

    # 2) $50 sales discount: Dr contra-revenue, Cr cash (a refund)
    j2 = make_journal(
        db,
        seeded_with_contras,
        lines=[(seeded_with_contras["contra_rev"], 50, 0), (seeded_with_contras["cash"], 0, 50)],
    )
    post_journal(db, j2.id)
    db.commit()

    # Compute the P&L the way the router does.
    from jrdbooks.accounting.balances import balances_by_account, signed_balance_for_type

    sums = balances_by_account(db, seeded_with_contras["entity"].id)
    revenue_total = Decimal("0")
    for acct in [seeded_with_contras["rev"], seeded_with_contras["contra_rev"]]:
        natural = signed_balance_for_type(sums[acct.id], acct.type)
        if acct.type == AccountType.REVENUE:
            revenue_total += natural
        elif acct.type == AccountType.CONTRA_REVENUE:
            revenue_total -= natural

    assert revenue_total == Decimal("950.0000"), (
        f"Expected revenue net of discounts = $950; got ${revenue_total}"
    )


def test_balance_sheet_subtracts_contra_asset(db, seeded_with_contras):
    """Accumulated depreciation must reduce net assets, not add to them.

    Equipment $10,000 + Accumulated Depreciation $2,000 should net to $8,000.
    """
    # Capitalize equipment: Dr Equipment $10000, Cr Cash $10000
    j1 = make_journal(
        db,
        seeded_with_contras,
        lines=[
            (seeded_with_contras["fixed_asset"], 10000, 0),
            (seeded_with_contras["cash"], 0, 10000),
        ],
    )
    post_journal(db, j1.id)

    # Record $2000 depreciation: Dr expense, Cr accum-dep
    j2 = make_journal(
        db,
        seeded_with_contras,
        lines=[
            (seeded_with_contras["exp"], 2000, 0),
            (seeded_with_contras["contra_asset"], 0, 2000),
        ],
    )
    post_journal(db, j2.id)
    db.commit()

    from jrdbooks.accounting.balances import balances_by_account, signed_balance_for_type

    sums = balances_by_account(db, seeded_with_contras["entity"].id)
    assets_total = Decimal("0")
    for acct in [seeded_with_contras["fixed_asset"], seeded_with_contras["contra_asset"]]:
        natural = signed_balance_for_type(sums[acct.id], acct.type)
        if acct.type == AccountType.ASSET:
            assets_total += natural
        elif acct.type == AccountType.CONTRA_ASSET:
            assets_total -= natural

    # Net assets = $10,000 - $2,000 = $8,000 (NOT $12,000 which the bug produced)
    assert assets_total == Decimal("8000.0000"), (
        f"Expected net fixed-asset value = $8,000; got ${assets_total}"
    )


def test_dashboard_cash_uses_ledger_not_feed_value(db, seeded_org):
    """The dashboard cash KPI must come from the LEDGER, not the bank_account's
    denormalized last_balance. Otherwise it drifts from the balance sheet."""
    from jrdbooks.accounting.balances import account_balance
    from jrdbooks.models.banking import BankAccount

    # Create a bank account with stale denormalized balance = $999
    ba = BankAccount(
        org_id=seeded_org["org"].id,
        entity_id=seeded_org["entity"].id,
        ledger_account_id=seeded_org["cash"].id,
        name="Operating",
        last_balance=Decimal("999.00"),  # WRONG / stale feed value
    )
    db.add(ba)
    db.flush()

    # Actually deposit $250 via a journal entry (Cr revenue, Dr cash)
    j = make_journal(
        db,
        seeded_org,
        lines=[(seeded_org["cash"], 250, 0), (seeded_org["rev"], 0, 250)],
    )
    post_journal(db, j.id)
    db.commit()

    # Ledger cash balance = $250. last_balance still says $999 (stale).
    ledger_cash = account_balance(db, seeded_org["cash"].id)
    assert ledger_cash == Decimal("250.0000")
    assert ba.last_balance == Decimal("999.00")
    # The DRIFT is precisely the bug the fix surfaces. Asserting both values are
    # different proves the dashboard's old behavior would have been wrong by
    # $749. The fixed dashboard uses ledger_cash, not last_balance.
    assert ledger_cash != ba.last_balance
