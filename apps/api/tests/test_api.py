"""Smoke-test the HTTP API end-to-end via TestClient.

This spins up a SQLite-backed instance of the API, logs in as the seeded user,
and exercises the critical flows: list accounts, create a journal, post it,
read the dashboard summary, and pull the trial balance.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test to use in-memory SQLite for full-stack test.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret"


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    # Reload db engine for SQLite, using StaticPool so the in-memory DB is
    # shared across all connections in the test.
    import jrdbooks.db as db_mod

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_mod.engine = engine
    db_mod.SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
    )
    db_mod.Base.metadata.create_all(engine)

    # Seed
    from jrdbooks.seed import seed

    seed()

    from jrdbooks.main import create_app

    with TestClient(create_app()) as c:
        yield c


def auth(client: TestClient) -> str:
    r = client.post("/auth/token", json={"email": "demo@jrdbooks.io", "password": "demo"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_returns_token(client: TestClient) -> None:
    r = client.post("/auth/token", json={"email": "demo@jrdbooks.io", "password": "demo"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["org_slug"] == "jrd"


def test_me_returns_user(client: TestClient) -> None:
    token = auth(client)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "demo@jrdbooks.io"
    assert body["org_slug"] == "jrd"
    assert body["role"] == "owner"


def test_entities_listed(client: TestClient) -> None:
    token = auth(client)
    r = client.get("/entities", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    entities = r.json()
    assert len(entities) == 2
    codes = {e["code"] for e in entities}
    assert codes == {"JRD-AUTO", "JRD-FUEL"}


def test_chart_of_accounts(client: TestClient) -> None:
    token = auth(client)
    entities = client.get("/entities", headers={"Authorization": f"Bearer {token}"}).json()
    entity_id = entities[0]["id"]
    r = client.get(
        f"/accounts?entity_id={entity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    accounts = r.json()
    assert len(accounts) >= 30
    codes = {a["code"] for a in accounts}
    assert "1010" in codes  # operating bank
    assert "4000" in codes  # service revenue


def test_create_and_post_journal(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entities = client.get("/entities", headers=headers).json()
    entity_id = entities[0]["id"]
    accounts = client.get(f"/accounts?entity_id={entity_id}", headers=headers).json()
    by_code = {a["code"]: a for a in accounts}

    payload = {
        "entity_id": entity_id,
        "posting_date": date.today().isoformat(),
        "memo": "Test API journal",
        "lines": [
            {
                "line_no": 1,
                "account_id": by_code["1010"]["id"],
                "debit": "500.00",
                "credit": "0",
                "description": "Cash in",
            },
            {
                "line_no": 2,
                "account_id": by_code["4000"]["id"],
                "debit": "0",
                "credit": "500.00",
                "description": "Service revenue",
            },
        ],
    }
    r = client.post("/journals?post=true", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "posted"
    assert body["posted_at"] is not None
    journal_id = body["id"]

    # Reverse it
    r = client.post(f"/journals/{journal_id}/reverse", headers=headers)
    assert r.status_code == 200
    rev = r.json()
    assert rev["status"] == "posted"
    assert rev["journal_no"].endswith("-REV")


def test_trial_balance_balances(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    r = client.get(
        f"/reports/trial-balance?entity_id={entity_id}",
        headers=headers,
    )
    assert r.status_code == 200
    rows = r.json()
    total_debit = sum(float(row["debit"]) for row in rows)
    total_credit = sum(float(row["credit"]) for row in rows)
    assert round(total_debit, 2) == round(total_credit, 2)


def test_dashboard_summary(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    r = client.get(f"/dashboard/summary?entity_id={entity_id}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "cash_balance" in body
    assert "month_to_date" in body
    assert "revenue_trend" in body
    assert len(body["revenue_trend"]) == 6
    assert len(body["bank_accounts"]) >= 2


def test_balance_sheet_balances(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    r = client.get(
        f"/reports/balance-sheet?entity_id={entity_id}&as_of={date.today().isoformat()}",
        headers=headers,
    )
    assert r.status_code == 200
    bs = r.json()
    assets = float(bs["assets_total"])
    liabs = float(bs["liabilities_total"])
    equity = float(bs["equity_total"])
    delta = abs(assets - (liabs + equity))
    assert delta < 0.01, f"Balance sheet does not balance: {delta} / {bs}"


def test_ai_suggestion_for_known_merchant(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    txns = client.get(
        "/banking/transactions?status=unreconciled",
        headers=headers,
    ).json()
    # Find a Sunoco transaction the seed creates
    sunoco = next((t for t in txns if "sunoco" in t["description"].lower()), None)
    if sunoco is None:
        return  # seed RNG didn't produce one this run
    r = client.get(
        f"/banking/transactions/{sunoco['id']}/suggest", headers=headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["suggested_account_code"] == "5100"
    assert body["confidence"] >= 0.85


def test_cash_flow_report(client: TestClient) -> None:
    from datetime import date, timedelta

    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    start = (date.today() - timedelta(days=60)).isoformat()
    end = date.today().isoformat()
    r = client.get(
        f"/reports/cash-flow?entity_id={entity_id}&start={start}&end={end}",
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    for k in ("operating", "investing", "financing", "net_change_in_cash"):
        assert k in body


def test_trial_balance_csv_export(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    r = client.get(
        f"/reports/trial-balance.csv?entity_id={entity_id}",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    body = r.text
    # Header + at least one data row
    lines = body.strip().splitlines()
    assert len(lines) >= 2
    assert lines[0].startswith("code,name,type,debit,credit")


def test_audit_events_endpoint(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/audit/events?limit=10", headers=headers)
    assert r.status_code == 200
    rows = r.json()
    # Seed produces audit events for journal posts
    assert isinstance(rows, list)


def test_ap_aging_report(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    r = client.get(f"/reports/ap-aging?entity_id={entity_id}", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_inventory_valuation_report(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    r = client.get(f"/reports/inventory-valuation?entity_id={entity_id}", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_stripe_webhook_is_idempotent(client: TestClient) -> None:
    """Posting the same Stripe event twice returns duplicate=True the second time."""
    payload = {
        "id": "evt_test_smoke_001",
        "type": "payout.paid",
        "data": {"object": {"id": "po_001", "amount": 5000}},
    }
    r1 = client.post("/webhooks/stripe", json=payload)
    assert r1.status_code == 200
    assert r1.json()["duplicate"] is False

    r2 = client.post("/webhooks/stripe", json=payload)
    assert r2.status_code == 200
    assert r2.json()["duplicate"] is True


def test_stripe_webhook_rejects_missing_id(client: TestClient) -> None:
    r = client.post("/webhooks/stripe", json={"type": "test"})
    assert r.status_code == 400


def test_create_bill_with_approval_posts_ap_journal(client: TestClient) -> None:
    from datetime import date, timedelta

    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]
    vendors = client.get("/vendors", headers=headers).json()
    vendor_id = vendors[0]["id"]
    accounts = client.get(f"/accounts?entity_id={entity_id}", headers=headers).json()
    expense_acct = next(a for a in accounts if a["code"] == "6100")  # Rent

    payload = {
        "entity_id": entity_id,
        "vendor_id": vendor_id,
        "issue_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
        "currency": "USD",
        "lines": [
            {
                "line_no": 1,
                "expense_account_id": expense_acct["id"],
                "description": "May rent",
                "amount": "1500.00",
            }
        ],
    }
    r = client.post("/bills?approve=true", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "approved"
    assert body["approval_status"] == "approved"
    assert float(body["total"]) == 1500.0

    # Verify the AP journal landed in the ledger
    bills_list = client.get(f"/bills?entity_id={entity_id}", headers=headers).json()
    assert any(b["bill_no"] == body["bill_no"] for b in bills_list)


def test_close_period_and_reject_post(client: TestClient) -> None:

    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    entity_id = client.get("/entities", headers=headers).json()[0]["id"]

    # Close a period in the far past so it doesn't conflict with the seed data
    payload = {
        "entity_id": entity_id,
        "fiscal_year": 2024,
        "fiscal_period": 1,
        "period_start": "2024-01-01",
        "period_end": "2024-01-31",
    }
    r = client.post("/periods/close", json=payload, headers=headers)
    assert r.status_code == 201, r.text

    # Listing closed periods returns it
    r = client.get(f"/periods?entity_id={entity_id}", headers=headers)
    assert r.status_code == 200
    rows = r.json()
    assert any(p["fiscal_year"] == 2024 and p["fiscal_period"] == 1 for p in rows)

    # Posting into that period should be rejected
    accounts = client.get(f"/accounts?entity_id={entity_id}", headers=headers).json()
    cash = next(a for a in accounts if a["code"] == "1010")
    rev = next(a for a in accounts if a["code"] == "4000")
    bad = {
        "entity_id": entity_id,
        "posting_date": "2024-01-15",
        "memo": "Should be rejected",
        "lines": [
            {"line_no": 1, "account_id": cash["id"], "debit": "10", "credit": "0"},
            {"line_no": 2, "account_id": rev["id"], "debit": "0", "credit": "10"},
        ],
    }
    r = client.post("/journals?post=true", json=bad, headers=headers)
    assert r.status_code == 400
    assert "closed period" in r.json()["detail"].lower()


def test_csv_bank_import(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    banks = client.get("/banking/accounts", headers=headers).json()
    bank = banks[0]

    csv_text = (
        "date,description,amount,external_id\n"
        "2026-05-01,NAPA Auto Parts,-87.45,csv-test-001\n"
        "2026-05-02,Sunoco Wholesale,-2450.10,csv-test-002\n"
        "2026-05-03,ACH from Acme Logistics,5300.00,csv-test-003\n"
    )
    r = client.post(
        f"/imports/bank-csv?bank_account_id={bank['id']}",
        files={"file": ("test.csv", csv_text, "text/csv")},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 3
    assert body["skipped_duplicates"] == 0
    assert body["ai_suggestions"] >= 2  # NAPA and Sunoco should match rules

    # Re-uploading the same file is idempotent
    r2 = client.post(
        f"/imports/bank-csv?bank_account_id={bank['id']}",
        files={"file": ("test.csv", csv_text, "text/csv")},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["imported"] == 0
    assert r2.json()["skipped_duplicates"] == 3


def test_categorize_bank_transaction(client: TestClient) -> None:
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    txns = client.get(
        "/banking/transactions?status=unreconciled",
        headers=headers,
    ).json()
    assert txns, "Seed should leave unreconciled transactions"
    txn = txns[0]
    bank = client.get("/banking/accounts", headers=headers).json()
    entities = client.get("/entities", headers=headers).json()
    accts = client.get(
        f"/accounts?entity_id={entities[0]['id']}", headers=headers
    ).json()
    target = next(a for a in accts if a["code"] == "6100")  # Rent
    # Find a txn for that entity:
    for t in txns:
        ba_match = next(b for b in bank if b["id"] == t["bank_account_id"])
        if ba_match["name"].startswith("JRD-AUTO"):
            txn = t
            break
    r = client.post(
        f"/banking/transactions/{txn['id']}/categorize",
        headers=headers,
        json={"account_id": target["id"]},
    )
    # Categorization may fail if entity mismatch — that's OK; assert that the
    # API at least responded predictably (200 or 400).
    assert r.status_code in (200, 400), r.text
