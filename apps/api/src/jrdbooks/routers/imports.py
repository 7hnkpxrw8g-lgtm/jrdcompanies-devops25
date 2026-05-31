"""CSV/OFX bank-feed import.

Accepts a CSV upload and creates BankTransaction rows on the target bank
account. Idempotent on `external_id` so re-uploading the same file is safe.

Expected CSV columns (case-insensitive, in any order):
    date, description, amount, [external_id], [merchant]
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai import suggest_for_transaction
from ..db import get_db
from ..models.audit import AuditEvent
from ..models.banking import BankAccount, BankTransaction, BankTxStatus
from ..security import AuthContext, require_org

router = APIRouter(prefix="/imports", tags=["imports"])


def _parse_date(s: str):
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s!r}")


def _parse_amount(s: str) -> Decimal:
    cleaned = s.strip().replace(",", "").replace("$", "")
    if not cleaned:
        return Decimal("0")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return Decimal(cleaned)


@router.post("/bank-csv")
async def import_bank_csv(
    bank_account_id: UUID,
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> dict:
    bank_account = db.get(BankAccount, bank_account_id)
    if bank_account is None or bank_account.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Bank account not found")

    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="Empty file")

    norm_fields = {(f or "").strip().lower(): f for f in reader.fieldnames}
    required = ["date", "description", "amount"]
    missing = [c for c in required if c not in norm_fields]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"CSV missing required columns: {missing}"
        )

    imported = 0
    skipped = 0
    errors: list[str] = []
    suggestions = 0
    for row_no, row in enumerate(reader, start=2):
        try:
            txn_date = _parse_date(row[norm_fields["date"]])
            description = row[norm_fields["description"]].strip()
            amount = _parse_amount(row[norm_fields["amount"]])
            external_id = (
                row[norm_fields["external_id"]].strip()
                if "external_id" in norm_fields
                else f"csv-{uuid4().hex[:12]}"
            )
            merchant = (
                row[norm_fields["merchant"]].strip()
                if "merchant" in norm_fields
                else None
            )
        except (KeyError, ValueError) as exc:
            errors.append(f"row {row_no}: {exc}")
            continue

        existing = (
            db.query(BankTransaction)
            .filter(
                BankTransaction.bank_account_id == bank_account.id,
                BankTransaction.external_id == external_id,
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        txn = BankTransaction(
            org_id=bank_account.org_id,
            entity_id=bank_account.entity_id,
            bank_account_id=bank_account.id,
            external_id=external_id,
            txn_date=txn_date,
            description=description,
            merchant=merchant,
            amount=amount,
            currency=bank_account.currency,
            status=BankTxStatus.UNRECONCILED,
            raw={"source": "csv", "row": row},
        )
        db.add(txn)
        db.flush()

        suggestion = suggest_for_transaction(db, txn)
        if suggestion.account_id:
            txn.suggested_account_id = UUID(suggestion.account_id)
            txn.ai_confidence = suggestion.confidence
            suggestions += 1
        imported += 1

    db.add(
        AuditEvent(
            org_id=ctx.org_id,
            entity_id=bank_account.entity_id,
            actor_user_id=ctx.user.id,
            source="api",
            action="bank_csv.import",
            target_kind="bank_account",
            target_id=bank_account.id,
            after={
                "imported": imported,
                "skipped_duplicates": skipped,
                "errors": len(errors),
                "ai_suggestions": suggestions,
                "filename": file.filename,
            },
        )
    )
    db.commit()
    return {
        "imported": imported,
        "skipped_duplicates": skipped,
        "ai_suggestions": suggestions,
        "errors": errors,
    }
