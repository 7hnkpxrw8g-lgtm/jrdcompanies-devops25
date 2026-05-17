"""Pydantic v2 request/response schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models.accounting import AccountType, JournalSource, JournalStatus


# ---------- Auth ----------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    org_id: UUID | None
    org_slug: str | None


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str
    org_id: UUID | None
    org_slug: str | None
    role: str | None


# ---------- Organizations / Entities ----------


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    name: str
    base_currency: str


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    legal_name: str | None
    currency: str
    industry: str | None


# ---------- Chart of accounts ----------


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    type: AccountType
    parent_id: UUID | None
    currency: str
    is_active: bool
    is_bank: bool
    is_cash: bool
    is_ar: bool
    is_ap: bool


class AccountCreate(BaseModel):
    entity_id: UUID
    code: str
    name: str
    type: AccountType
    parent_id: UUID | None = None
    currency: str = "USD"
    is_bank: bool = False
    is_cash: bool = False
    is_ar: bool = False
    is_ap: bool = False


# ---------- Journals ----------


class JournalLineIn(BaseModel):
    line_no: int = Field(ge=1)
    account_id: UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    description: str | None = None
    customer_id: UUID | None = None
    vendor_id: UUID | None = None


class JournalCreate(BaseModel):
    entity_id: UUID
    journal_no: str | None = None
    posting_date: date
    memo: str | None = None
    source: JournalSource = JournalSource.MANUAL
    source_ref: str | None = None
    currency: str = "USD"
    fx_rate: Decimal = Decimal("1")
    lines: list[JournalLineIn]


class JournalLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    line_no: int
    account_id: UUID
    debit: Decimal
    credit: Decimal
    description: str | None


class JournalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    journal_no: str
    posting_date: date
    memo: str | None
    status: JournalStatus
    source: JournalSource
    source_ref: str | None
    currency: str
    fx_rate: Decimal
    posted_at: datetime | None
    lines: list[JournalLineOut]


# ---------- Customers / Vendors ----------


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    display_name: str
    email: str | None
    phone: str | None
    payment_terms_days: int
    currency: str
    is_active: bool


class CustomerCreate(BaseModel):
    code: str
    display_name: str
    email: EmailStr | None = None
    phone: str | None = None
    payment_terms_days: int = 30
    currency: str = "USD"


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    display_name: str
    email: str | None
    default_terms_days: int
    currency: str
    is_1099: bool
    is_active: bool


class VendorCreate(BaseModel):
    code: str
    display_name: str
    email: EmailStr | None = None
    phone: str | None = None
    default_terms_days: int = 30
    currency: str = "USD"
    is_1099: bool = False


# ---------- Invoices ----------


class InvoiceLineIn(BaseModel):
    line_no: int = Field(ge=1)
    revenue_account_id: UUID
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal
    tax_rate: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    kind: str = "service"


class InvoiceCreate(BaseModel):
    entity_id: UUID
    customer_id: UUID
    invoice_no: str | None = None
    issue_date: date
    due_date: date
    currency: str = "USD"
    notes: str | None = None
    lines: list[InvoiceLineIn]


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    discount_amount: Decimal
    line_total: Decimal


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    invoice_no: str
    customer_id: UUID
    issue_date: date
    due_date: date
    status: str
    currency: str
    subtotal: Decimal
    tax_total: Decimal
    discount_total: Decimal
    total: Decimal
    amount_paid: Decimal
    lines: list[InvoiceLineOut]


# ---------- Bank ----------


class BankAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    institution: str | None
    mask: str | None
    account_type: str
    currency: str
    last_balance: Decimal
    last_sync_at: datetime | None


class BankTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bank_account_id: UUID
    txn_date: date
    description: str
    merchant: str | None
    amount: Decimal
    status: str
    suggested_account_id: UUID | None
    ai_confidence: Decimal | None


# ---------- Reports ----------


class TrialBalanceRow(BaseModel):
    account_id: UUID
    code: str
    name: str
    type: str
    debit: Decimal
    credit: Decimal


class PnLRow(BaseModel):
    account_id: UUID
    code: str
    name: str
    amount: Decimal


class PnLResponse(BaseModel):
    entity_id: UUID
    start: date
    end: date
    revenue: list[PnLRow]
    expense: list[PnLRow]
    revenue_total: Decimal
    expense_total: Decimal
    net_income: Decimal


class BalanceSheetRow(BaseModel):
    account_id: UUID
    code: str
    name: str
    balance: Decimal


class BalanceSheetResponse(BaseModel):
    entity_id: UUID
    as_of: date
    assets: list[BalanceSheetRow]
    liabilities: list[BalanceSheetRow]
    equity: list[BalanceSheetRow]
    assets_total: Decimal
    liabilities_total: Decimal
    equity_total: Decimal
    retained_earnings: Decimal
