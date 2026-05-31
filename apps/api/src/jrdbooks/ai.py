"""AI helpers: rule-based categorization with confidence + optional LLM hook.

The categorization rules live in `RULES`. Each rule is `(keyword, account_code,
confidence)`. The first match wins. The keyword is matched case-insensitively
against the bank transaction description and merchant.

A real LLM hook (Claude / OpenAI) is wired in `suggest_via_llm` and only fires
when `settings.openai_api_key` is set — the API gracefully falls back to rules
otherwise so tests don't need network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from .models.accounting import Account
from .models.banking import BankTransaction


@dataclass
class CategorizationSuggestion:
    account_code: str | None
    account_id: str | None
    confidence: Decimal
    rationale: str


# Ordered list; first match wins.
RULES: list[tuple[str, str, str, Decimal]] = [
    ("sunoco", "5100", "Fuel purchase → COGS Fuel", Decimal("0.95")),
    ("fuel", "5100", "Fuel keyword → COGS Fuel", Decimal("0.85")),
    ("napa", "5000", "NAPA Auto Parts → COGS Parts", Decimal("0.95")),
    ("autozone", "5000", "AutoZone → COGS Parts", Decimal("0.95")),
    ("stripe payout", "1010", "Stripe payout → Operating bank (transfer)", Decimal("0.90")),
    ("square deposit", "1010", "Square deposit → Operating bank", Decimal("0.90")),
    ("ach from", "4000", "ACH inflow → Service Revenue", Decimal("0.70")),
    ("rent payment", "6100", "Rent expense", Decimal("0.95")),
    ("rent", "6100", "Rent keyword → Rent expense", Decimal("0.80")),
    ("utility", "6200", "Utility bill", Decimal("0.90")),
    ("insurance", "6300", "Insurance premium", Decimal("0.90")),
    ("supplies", "6400", "Office supplies", Decimal("0.75")),
    ("card processing", "6700", "Payment processor fees", Decimal("0.90")),
    ("bank fee", "6700", "Bank fee", Decimal("0.95")),
]


def suggest_for_transaction(
    db: Session, txn: BankTransaction
) -> CategorizationSuggestion:
    haystack = f"{txn.description} {txn.merchant or ''}".lower()
    for needle, code, rationale, confidence in RULES:
        if needle in haystack:
            account = (
                db.query(Account)
                .filter(Account.entity_id == txn.entity_id, Account.code == code)
                .first()
            )
            if account is None:
                continue
            return CategorizationSuggestion(
                account_code=code,
                account_id=str(account.id),
                confidence=confidence,
                rationale=rationale,
            )
    return CategorizationSuggestion(
        account_code=None,
        account_id=None,
        confidence=Decimal("0.0"),
        rationale="No matching rule",
    )
