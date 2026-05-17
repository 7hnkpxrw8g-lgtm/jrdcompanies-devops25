"""Accounting engine: posting, reporting, period-close.

Public API:
    post_journal(db, journal_id, actor_user_id) -> Journal
    reverse_journal(db, journal_id, actor_user_id, posting_date) -> Journal
    account_balance(db, account_id, as_of=None) -> Decimal
"""

from .balances import account_balance, balances_by_account, trial_balance
from .posting import PostingError, post_journal, reverse_journal

__all__ = [
    "PostingError",
    "account_balance",
    "balances_by_account",
    "post_journal",
    "reverse_journal",
    "trial_balance",
]
