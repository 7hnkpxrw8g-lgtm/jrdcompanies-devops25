"""Bank accounts, bank transactions, reconciliation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..accounting import PostingError, post_journal
from ..db import get_db
from ..models.accounting import Account, Journal, JournalLine, JournalSource
from ..models.audit import AuditEvent
from ..models.banking import BankAccount, BankTransaction, BankTxStatus, ReconciliationMatch
from ..schemas import BankAccountOut, BankTransactionOut
from ..security import AuthContext, require_org

router = APIRouter(prefix="/banking", tags=["banking"])


class CategorizeRequest(BaseModel):
    account_id: UUID
    memo: str | None = None


@router.get("/accounts", response_model=list[BankAccountOut])
def list_bank_accounts(
    entity_id: UUID | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[BankAccountOut]:
    q = db.query(BankAccount).filter(BankAccount.org_id == ctx.org_id)
    if entity_id:
        q = q.filter(BankAccount.entity_id == entity_id)
    return [BankAccountOut.model_validate(r) for r in q.order_by(BankAccount.name).all()]


@router.get("/transactions", response_model=list[BankTransactionOut])
def list_bank_transactions(
    bank_account_id: UUID | None = None,
    status: BankTxStatus | None = None,
    start: date | None = None,
    end: date | None = None,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> list[BankTransactionOut]:
    q = db.query(BankTransaction).filter(BankTransaction.org_id == ctx.org_id)
    if bank_account_id:
        q = q.filter(BankTransaction.bank_account_id == bank_account_id)
    if status:
        q = q.filter(BankTransaction.status == status)
    if start:
        q = q.filter(BankTransaction.txn_date >= start)
    if end:
        q = q.filter(BankTransaction.txn_date <= end)
    return [
        BankTransactionOut.model_validate(r)
        for r in q.order_by(BankTransaction.txn_date.desc()).limit(500).all()
    ]


@router.post("/transactions/{txn_id}/categorize", response_model=BankTransactionOut)
def categorize_transaction(
    txn_id: UUID,
    payload: CategorizeRequest,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> BankTransactionOut:
    """Book a journal entry for a bank transaction.

    Outflow (negative amount): debit chosen expense/asset, credit bank.
    Inflow (positive amount): debit bank, credit chosen revenue/liability.
    """
    txn = db.get(BankTransaction, txn_id)
    if txn is None or txn.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Bank transaction not found")
    if txn.status == BankTxStatus.POSTED:
        raise HTTPException(status_code=400, detail="Transaction already posted")

    bank_account = db.get(BankAccount, txn.bank_account_id)
    assert bank_account is not None

    other_account = db.get(Account, payload.account_id)
    if other_account is None or other_account.entity_id != txn.entity_id:
        raise HTTPException(status_code=400, detail="Target account not in entity")

    amount = abs(txn.amount).quantize(Decimal("0.0001"))
    if amount == 0:
        raise HTTPException(status_code=400, detail="Zero-amount transaction")

    journal = Journal(
        org_id=txn.org_id,
        entity_id=txn.entity_id,
        journal_no=f"BNK-{txn.id.hex[:8].upper()}",
        posting_date=txn.txn_date,
        memo=payload.memo or txn.description,
        source=JournalSource.BANK,
        source_ref=str(txn.id),
        currency=txn.currency,
    )
    db.add(journal)
    db.flush()

    bank_ledger_acct = bank_account.ledger_account_id
    if txn.amount < 0:
        # outflow: debit other, credit bank
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=1,
                account_id=other_account.id,
                debit=amount,
                credit=Decimal("0"),
                description=txn.description,
            )
        )
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=2,
                account_id=bank_ledger_acct,
                debit=Decimal("0"),
                credit=amount,
                description=txn.description,
            )
        )
    else:
        # inflow: debit bank, credit other
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=1,
                account_id=bank_ledger_acct,
                debit=amount,
                credit=Decimal("0"),
                description=txn.description,
            )
        )
        db.add(
            JournalLine(
                journal_id=journal.id,
                line_no=2,
                account_id=other_account.id,
                debit=Decimal("0"),
                credit=amount,
                description=txn.description,
            )
        )
    db.flush()
    db.refresh(journal)
    try:
        post_journal(db, journal.id, actor_user_id=ctx.user.id)
    except PostingError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    txn.journal_id = journal.id
    txn.status = BankTxStatus.POSTED

    bank_ledger_entry = next(
        (e for e in journal.lines if e.account_id == bank_ledger_acct), None
    )
    if bank_ledger_entry is not None:
        # The matching ledger entry is the row written for the bank line.
        from ..models.accounting import LedgerEntry

        le = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.journal_line_id == bank_ledger_entry.id)
            .one()
        )
        db.add(
            ReconciliationMatch(
                org_id=txn.org_id,
                bank_transaction_id=txn.id,
                ledger_entry_id=le.id,
                matched_by=ctx.user.id,
                confidence=Decimal("1.0"),
                notes="Categorized from bank feed",
            )
        )

    db.add(
        AuditEvent(
            org_id=ctx.org_id,
            entity_id=txn.entity_id,
            actor_user_id=ctx.user.id,
            source="api",
            action="bank_tx.categorize",
            target_kind="bank_transaction",
            target_id=txn.id,
            after={
                "amount": float(txn.amount),
                "target_account": other_account.code,
                "journal_id": str(journal.id),
            },
        )
    )

    db.commit()
    db.refresh(txn)
    return BankTransactionOut.model_validate(txn)
