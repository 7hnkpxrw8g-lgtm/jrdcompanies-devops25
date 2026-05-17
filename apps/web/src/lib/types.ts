// TS mirrors of the most-used API schemas.

export interface User {
  id: string;
  email: string;
  full_name: string;
  org_id: string | null;
  org_slug: string | null;
  role: string | null;
}

export interface Organization {
  id: string;
  slug: string;
  name: string;
  base_currency: string;
}

export interface Entity {
  id: string;
  code: string;
  name: string;
  legal_name: string | null;
  currency: string;
  industry: string | null;
}

export interface Account {
  id: string;
  code: string;
  name: string;
  type: string;
  parent_id: string | null;
  currency: string;
  is_active: boolean;
  is_bank: boolean;
  is_cash: boolean;
  is_ar: boolean;
  is_ap: boolean;
}

export interface JournalLine {
  id?: string;
  line_no: number;
  account_id: string;
  debit: string | number;
  credit: string | number;
  description?: string | null;
}

export interface Journal {
  id: string;
  journal_no: string;
  posting_date: string;
  memo: string | null;
  status: "draft" | "posted" | "reversed";
  source: string;
  source_ref: string | null;
  currency: string;
  fx_rate: string;
  posted_at: string | null;
  lines: JournalLine[];
}

export interface BankAccount {
  id: string;
  name: string;
  institution: string | null;
  mask: string | null;
  account_type: string;
  currency: string;
  last_balance: string;
  last_sync_at: string | null;
}

export interface BankTransaction {
  id: string;
  bank_account_id: string;
  txn_date: string;
  description: string;
  merchant: string | null;
  amount: string;
  status: "unreconciled" | "matched" | "posted" | "ignored";
  suggested_account_id: string | null;
  ai_confidence: string | null;
}

export interface DashboardSummary {
  cash_balance: number;
  month_to_date: { revenue: number; expense: number; net_income: number };
  unreconciled_count: number;
  ar_outstanding: number;
  ap_outstanding: number;
  bank_accounts: { id: string; name: string; balance: number; currency: string }[];
  revenue_trend: { month: string; revenue: number; expense: number; net_income: number }[];
}

export interface PnLRow {
  account_id: string;
  code: string;
  name: string;
  amount: string;
}

export interface PnLResponse {
  entity_id: string;
  start: string;
  end: string;
  revenue: PnLRow[];
  expense: PnLRow[];
  revenue_total: string;
  expense_total: string;
  net_income: string;
}

export interface BalanceSheetRow {
  account_id: string;
  code: string;
  name: string;
  balance: string;
}

export interface BalanceSheetResponse {
  entity_id: string;
  as_of: string;
  assets: BalanceSheetRow[];
  liabilities: BalanceSheetRow[];
  equity: BalanceSheetRow[];
  assets_total: string;
  liabilities_total: string;
  equity_total: string;
  retained_earnings: string;
}

export interface TrialBalanceRow {
  account_id: string;
  code: string;
  name: string;
  type: string;
  debit: string;
  credit: string;
}

export interface Customer {
  id: string;
  code: string;
  display_name: string;
  email: string | null;
  phone: string | null;
  payment_terms_days: number;
  currency: string;
  is_active: boolean;
}

export interface Vendor {
  id: string;
  code: string;
  display_name: string;
  email: string | null;
  default_terms_days: number;
  currency: string;
  is_1099: boolean;
  is_active: boolean;
}

export interface Invoice {
  id: string;
  invoice_no: string;
  customer_id: string;
  issue_date: string;
  due_date: string;
  status: string;
  currency: string;
  subtotal: string;
  tax_total: string;
  discount_total: string;
  total: string;
  amount_paid: string;
  lines: {
    id: string;
    line_no: number;
    description: string;
    quantity: string;
    unit_price: string;
    tax_rate: string;
    discount_amount: string;
    line_total: string;
  }[];
}
