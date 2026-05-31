"""Initial schema: core, accounting, banking, commerce, inventory, fuel, repair, payroll, integrations, audit.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- core ----
    op.create_table(
        "organization",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("fiscal_year_start_month", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "entity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255)),
        sa.Column("tax_id", sa.String(64)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/New_York"),
        sa.Column("industry", sa.String(64)),
        sa.Column("is_consolidation_target", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "code", name="entity_org_code"),
    )

    op.create_table(
        "user_account",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    role_enum = postgresql.ENUM(
        "owner", "admin", "accountant", "approver", "clerk", "viewer",
        name="role_enum", create_type=True,
    )
    role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "membership",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", postgresql.ENUM(name="role_enum", create_type=False), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "user_id", name="membership_org_user"),
    )

    # ---- accounting ----
    account_type = postgresql.ENUM(
        "asset", "liability", "equity", "revenue", "expense",
        "contra_asset", "contra_liability", "contra_revenue",
        name="account_type_enum", create_type=True,
    )
    account_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "account",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id", ondelete="SET NULL")),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", postgresql.ENUM(name="account_type_enum", create_type=False), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_bank", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_cash", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_ar", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_ap", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entity_id", "code", name="account_entity_code"),
    )
    op.create_index("ix_account_org_entity", "account", ["org_id", "entity_id"])

    journal_status = postgresql.ENUM(
        "draft", "posted", "reversed", name="journal_status_enum", create_type=True
    )
    journal_status.create(op.get_bind(), checkfirst=True)
    journal_source = postgresql.ENUM(
        "manual", "invoice", "bill", "payment", "bank", "payroll",
        "fuel", "inventory", "integration", "system",
        name="journal_source_enum", create_type=True,
    )
    journal_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "journal",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id", ondelete="CASCADE"), nullable=False),
        sa.Column("journal_no", sa.String(32), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("memo", sa.Text()),
        sa.Column("status", postgresql.ENUM(name="journal_status_enum", create_type=False), nullable=False, server_default="draft"),
        sa.Column("source", postgresql.ENUM(name="journal_source_enum", create_type=False), nullable=False, server_default="manual"),
        sa.Column("source_ref", sa.String(128)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("fx_rate", sa.Numeric(18, 8), nullable=False, server_default="1"),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("posted_by", postgresql.UUID(as_uuid=True)),
        sa.Column("reversed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id", ondelete="SET NULL")),
        sa.Column("reverses_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id", ondelete="SET NULL")),
        sa.Column("extra", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("(status::text <> 'posted') OR (posted_at IS NOT NULL)", name="posted_requires_posted_at"),
    )
    op.create_index("ix_journal_org_entity_date", "journal", ["org_id", "entity_id", "posting_date"])
    op.create_index("ix_journal_status", "journal", ["status"])

    op.create_table(
        "journal_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("debit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("description", sa.Text()),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True)),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("extra", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("debit >= 0", name="debit_nonneg"),
        sa.CheckConstraint("credit >= 0", name="credit_nonneg"),
        sa.CheckConstraint("(debit = 0 AND credit > 0) OR (debit > 0 AND credit = 0)", name="debit_xor_credit"),
    )

    op.create_table(
        "ledger_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id"), nullable=False),
        sa.Column("journal_line_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal_line.id"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("fx_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("reverses_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ledger_entry.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount <> 0", name="amount_nonzero"),
    )
    op.create_index(
        "ix_ledger_org_entity_account_date",
        "ledger_entry",
        ["org_id", "entity_id", "account_id", "posting_date"],
    )
    op.create_index("ix_ledger_journal", "ledger_entry", ["journal_id"])

    op.create_table(
        "period_close",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_period", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True)),
        sa.Column("retained_earnings_journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entity_id", "fiscal_year", "fiscal_period", name="period_close_unique"),
    )

    # ---- commerce ----
    doc_status = postgresql.ENUM(
        "draft", "approved", "sent", "partial", "paid", "void", "overdue",
        name="doc_status_enum", create_type=True,
    )
    doc_status.create(op.get_bind(), checkfirst=True)

    line_item_kind = postgresql.ENUM(
        "service", "product", "labor", "part", "fuel", "discount", "tax", "shipping",
        name="line_item_kind_enum", create_type=True,
    )
    line_item_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "customer",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(64)),
        sa.Column("billing_address", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("shipping_address", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("tax_id", sa.String(64)),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "code", name="customer_org_code"),
    )

    op.create_table(
        "vendor",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(64)),
        sa.Column("address", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("tax_id", sa.String(64)),
        sa.Column("default_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_1099", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "code", name="vendor_org_code"),
    )

    # ---- inventory (forward-declared, used by invoice_line FK) ----
    op.create_table(
        "inventory_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("unit", sa.String(16), nullable=False, server_default="ea"),
        sa.Column("inventory_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("cogs_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("revenue_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("on_hand", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("last_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "sku", name="inventory_item_org_sku"),
    )

    op.create_table(
        "stock_lot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_item.id"), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(18, 4), nullable=False),
        sa.Column("quantity_received", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("source_ref", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    movement_kind = postgresql.ENUM(
        "receipt", "sale", "adjustment", "transfer",
        name="movement_kind_enum", create_type=True,
    )
    movement_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "inventory_movement",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_item.id"), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("kind", postgresql.ENUM(name="movement_kind_enum", create_type=False), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_inventory_movement_item_date", "inventory_movement", ["item_id", "movement_date"])

    # ---- commerce documents ----
    op.create_table(
        "invoice",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("invoice_no", sa.String(64), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="doc_status_enum", create_type=False), nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("discount_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "invoice_no", name="invoice_org_no"),
    )
    op.create_index("ix_invoice_status", "invoice", ["status"])
    op.create_index("ix_invoice_customer", "invoice", ["customer_id"])

    op.create_table(
        "invoice_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("kind", postgresql.ENUM(name="line_item_kind_enum", create_type=False), nullable=False, server_default="service"),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_item.id")),
        sa.Column("revenue_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_rate", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="qty_positive"),
        sa.CheckConstraint("unit_price >= 0", name="unit_price_nonneg"),
    )

    op.create_table(
        "bill",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendor.id"), nullable=False),
        sa.Column("bill_no", sa.String(64), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="doc_status_enum", create_type=False), nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("approval_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "bill_no", name="bill_org_no"),
    )
    op.create_index("ix_bill_status", "bill", ["status"])
    op.create_index("ix_bill_vendor", "bill", ["vendor_id"])

    # ---- banking ----
    bank_tx_status = postgresql.ENUM(
        "unreconciled", "matched", "posted", "ignored",
        name="bank_tx_status_enum", create_type=True,
    )
    bank_tx_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bank_account",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("ledger_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("institution", sa.String(255)),
        sa.Column("mask", sa.String(8)),
        sa.Column("account_type", sa.String(32), nullable=False, server_default="checking"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("external_id", sa.String(128)),
        sa.Column("provider", sa.String(32)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "external_id", name="bank_account_ext"),
    )

    op.create_table(
        "bank_transaction",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_account.id"), nullable=False),
        sa.Column("external_id", sa.String(128)),
        sa.Column("txn_date", sa.Date(), nullable=False),
        sa.Column("posted_date", sa.Date()),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("merchant", sa.String(255)),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", postgresql.ENUM(name="bank_tx_status_enum", create_type=False), nullable=False, server_default="unreconciled"),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("suggested_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id")),
        sa.Column("ai_confidence", sa.Numeric(5, 4)),
        sa.Column("raw", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("bank_account_id", "external_id", name="bank_tx_ext"),
    )
    op.create_index("ix_bank_tx_status", "bank_transaction", ["status"])
    op.create_index("ix_bank_tx_date", "bank_transaction", ["txn_date"])

    op.create_table(
        "reconciliation_match",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("bank_transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_transaction.id"), nullable=False, unique=True),
        sa.Column("ledger_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ledger_entry.id"), nullable=False),
        sa.Column("matched_by", postgresql.UUID(as_uuid=True)),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="1.0"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---- fuel ops ----
    op.create_table(
        "fuel_tank",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("fuel_type", sa.String(32), nullable=False),
        sa.Column("capacity_gallons", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_volume", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("weighted_avg_cost", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("inventory_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("cogs_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entity_id", "name", name="fuel_tank_entity_name"),
    )

    op.create_table(
        "fuel_delivery",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fuel_tank.id"), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendor.id")),
        sa.Column("invoice_no", sa.String(64)),
        sa.Column("gallons", sa.Numeric(12, 4), nullable=False),
        sa.Column("cost_per_gallon", sa.Numeric(12, 6), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fuel_delivery_tank_date", "fuel_delivery", ["tank_id", "delivery_date"])

    op.create_table(
        "fuel_dispense",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fuel_tank.id"), nullable=False),
        sa.Column("dispense_date", sa.Date(), nullable=False),
        sa.Column("pump_id", sa.String(32)),
        sa.Column("gallons_sold", sa.Numeric(12, 4), nullable=False),
        sa.Column("gross_revenue", sa.Numeric(18, 4), nullable=False),
        sa.Column("stick_reading_gallons", sa.Numeric(12, 4)),
        sa.Column("variance_gallons", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("variance_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fuel_dispense_tank_date", "fuel_dispense", ["tank_id", "dispense_date"])

    # ---- repair ops ----
    ro_status = postgresql.ENUM(
        "draft", "in_progress", "awaiting_parts", "ready", "completed", "invoiced", "cancelled",
        name="ro_status_enum", create_type=True,
    )
    ro_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "repair_order",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("ro_no", sa.String(64), nullable=False),
        sa.Column("opened_date", sa.Date(), nullable=False),
        sa.Column("closed_date", sa.Date()),
        sa.Column("status", postgresql.ENUM(name="ro_status_enum", create_type=False), nullable=False, server_default="draft"),
        sa.Column("vehicle_vin", sa.String(32)),
        sa.Column("vehicle_year", sa.Integer()),
        sa.Column("vehicle_make", sa.String(64)),
        sa.Column("vehicle_model", sa.String(64)),
        sa.Column("odometer_in", sa.Integer()),
        sa.Column("odometer_out", sa.Integer()),
        sa.Column("technician", sa.String(255)),
        sa.Column("labor_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("parts_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoice.id")),
        sa.Column("external_id", sa.String(128)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "ro_no", name="ro_org_no"),
    )

    op.create_table(
        "repair_order_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repair_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repair_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_item.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ro_line_ro", "repair_order_line", ["repair_order_id"])

    # ---- payroll ----
    payroll_status = postgresql.ENUM(
        "draft", "approved", "paid", "void",
        name="payroll_status_enum", create_type=True,
    )
    payroll_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payroll_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("run_no", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="payroll_status_enum", create_type=False), nullable=False, server_default="draft"),
        sa.Column("gross_wages", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("employer_taxes", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("employee_taxes", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("net_pay", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entity_id", "run_no", name="payroll_entity_no"),
    )

    op.create_table(
        "payslip",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payroll_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_name", sa.String(255), nullable=False),
        sa.Column("employee_external_id", sa.String(128)),
        sa.Column("gross", sa.Numeric(18, 4), nullable=False),
        sa.Column("employee_taxes", sa.Numeric(18, 4), nullable=False),
        sa.Column("employer_taxes", sa.Numeric(18, 4), nullable=False),
        sa.Column("net", sa.Numeric(18, 4), nullable=False),
        sa.Column("deductions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payslip_run", "payslip", ["run_id"])

    # ---- integrations ----
    integration_provider = postgresql.ENUM(
        "plaid", "stripe", "square", "coinbase", "tekmetric", "shopify",
        "gmail", "outlook", "quickbooks", "csv",
        name="integration_provider_enum", create_type=True,
    )
    integration_provider.create(op.get_bind(), checkfirst=True)

    integration_status = postgresql.ENUM(
        "pending", "connected", "error", "disconnected",
        name="integration_status_enum", create_type=True,
    )
    integration_status.create(op.get_bind(), checkfirst=True)

    sync_run_status = postgresql.ENUM(
        "running", "success", "partial", "failed",
        name="sync_run_status_enum", create_type=True,
    )
    sync_run_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "integration_connection",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id")),
        sa.Column("provider", postgresql.ENUM(name="integration_provider_enum", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM(name="integration_status_enum", create_type=False), nullable=False, server_default="pending"),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("external_account_id", sa.String(255)),
        sa.Column("access_token_encrypted", sa.Text()),
        sa.Column("refresh_token_encrypted", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "provider", "external_account_id", name="integration_unique_account"),
    )

    op.create_table(
        "integration_sync_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("integration_connection.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", postgresql.ENUM(name="sync_run_status_enum", create_type=False), nullable=False),
        sa.Column("records_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_sync_run_conn_started", "integration_sync_run", ["connection_id", "started_at"])

    op.create_table(
        "webhook_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id")),
        sa.Column("provider", postgresql.ENUM(name="integration_provider_enum", create_type=False), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("external_event_id", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("processing_error", sa.Text()),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "external_event_id", name="webhook_event_unique"),
    )
    op.create_index("ix_webhook_received", "webhook_event", ["received_at"])

    # ---- audit ----
    op.create_table(
        "audit_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entity.id")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_label", sa.String(255)),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_kind", sa.String(64), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("request_id", sa.String(64)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("before", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("after", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_org_at", "audit_event", ["org_id", "occurred_at"])
    op.create_index("ix_audit_target", "audit_event", ["target_kind", "target_id"])


def downgrade() -> None:
    # Drop in reverse FK order
    for table in [
        "audit_event", "webhook_event", "integration_sync_run", "integration_connection",
        "payslip", "payroll_run", "repair_order_line", "repair_order",
        "fuel_dispense", "fuel_delivery", "fuel_tank",
        "reconciliation_match", "bank_transaction", "bank_account",
        "bill", "invoice_line", "invoice",
        "inventory_movement", "stock_lot", "inventory_item",
        "vendor", "customer",
        "period_close", "ledger_entry", "journal_line", "journal", "account",
        "membership", "user_account", "entity", "organization",
    ]:
        op.drop_table(table)

    for enum_name in [
        "sync_run_status_enum", "integration_status_enum", "integration_provider_enum",
        "payroll_status_enum", "ro_status_enum", "bank_tx_status_enum",
        "movement_kind_enum", "line_item_kind_enum", "doc_status_enum",
        "journal_source_enum", "journal_status_enum", "account_type_enum", "role_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
