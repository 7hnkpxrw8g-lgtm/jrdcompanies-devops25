"""Webhook ingestion endpoints with idempotency.

These endpoints accept the raw payload, persist it in `webhook_event` keyed
by `(provider, external_event_id)` so retries are idempotent, and dispatch
to a per-provider handler. Real signature verification stubs are in place
when the corresponding secret is configured.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.integrations import IntegrationProvider, WebhookEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

settings = get_settings()


def _ingest(
    db: Session,
    provider: IntegrationProvider,
    event_type: str,
    external_event_id: str,
    payload: dict,
) -> tuple[WebhookEvent, bool]:
    """Returns (event, created). Returns existing event on duplicate IDs."""
    existing = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.provider == provider,
            WebhookEvent.external_event_id == external_event_id,
        )
        .first()
    )
    if existing:
        return existing, False
    evt = WebhookEvent(
        provider=provider,
        event_type=event_type,
        external_event_id=external_event_id,
        payload=payload,
        received_at=datetime.now(UTC),
    )
    db.add(evt)
    db.flush()
    db.commit()
    return evt, True


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verify a Stripe-Signature header. Returns False if no secret is configured."""
    if not secret or not sig_header:
        return False
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t")
    expected = parts.get("v1")
    if not (timestamp and expected):
        return False
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    raw = await request.body()
    if settings.stripe_webhook_secret and not _verify_stripe_signature(
        raw, stripe_signature or "", settings.stripe_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="invalid_signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    external_id = str(payload.get("id") or "")
    event_type = str(payload.get("type") or "unknown")
    if not external_id:
        raise HTTPException(status_code=400, detail="missing event id")

    evt, created = _ingest(
        db, IntegrationProvider.STRIPE, event_type, external_id, payload
    )
    return {
        "received": True,
        "event_id": str(evt.id),
        "external_event_id": external_id,
        "duplicate": not created,
    }


@router.post("/plaid")
async def plaid_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    external_id = str(
        (payload.get("webhook_code") and payload.get("item_id")
        and f"{payload['webhook_code']}-{payload['item_id']}")
        or payload.get("request_id")
        or ""
    )
    event_type = str(payload.get("webhook_type") or payload.get("webhook_code") or "unknown")
    if not external_id:
        raise HTTPException(status_code=400, detail="missing event id")

    evt, created = _ingest(
        db, IntegrationProvider.PLAID, event_type, external_id, payload
    )
    return {
        "received": True,
        "event_id": str(evt.id),
        "external_event_id": external_id,
        "duplicate": not created,
    }


@router.get("/events")
def list_webhook_events(
    provider: IntegrationProvider | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(WebhookEvent)
    if provider:
        q = q.filter(WebhookEvent.provider == provider)
    rows = q.order_by(WebhookEvent.received_at.desc()).limit(limit).all()
    return [
        {
            "id": str(r.id),
            "provider": r.provider.value,
            "event_type": r.event_type,
            "external_event_id": r.external_event_id,
            "received_at": r.received_at.isoformat() if r.received_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in rows
    ]
