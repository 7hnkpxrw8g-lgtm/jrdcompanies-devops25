"""Customers + vendors CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.commerce import Customer, Vendor
from ..schemas import CustomerCreate, CustomerOut, VendorCreate, VendorOut
from ..security import AuthContext, require_org

router = APIRouter(tags=["contacts"])


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(
    ctx: AuthContext = Depends(require_org), db: Session = Depends(get_db)
) -> list[CustomerOut]:
    rows = (
        db.query(Customer)
        .filter(Customer.org_id == ctx.org_id)
        .order_by(Customer.display_name)
        .all()
    )
    return [CustomerOut.model_validate(r) for r in rows]


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(
    payload: CustomerCreate,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> CustomerOut:
    if db.query(Customer).filter(
        Customer.org_id == ctx.org_id, Customer.code == payload.code
    ).first():
        raise HTTPException(status_code=409, detail="Customer code already exists")
    customer = Customer(
        org_id=ctx.org_id,
        code=payload.code,
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
        payment_terms_days=payload.payment_terms_days,
        currency=payload.currency,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return CustomerOut.model_validate(customer)


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(
    ctx: AuthContext = Depends(require_org), db: Session = Depends(get_db)
) -> list[VendorOut]:
    rows = (
        db.query(Vendor)
        .filter(Vendor.org_id == ctx.org_id)
        .order_by(Vendor.display_name)
        .all()
    )
    return [VendorOut.model_validate(r) for r in rows]


@router.post("/vendors", response_model=VendorOut, status_code=201)
def create_vendor(
    payload: VendorCreate,
    ctx: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> VendorOut:
    if db.query(Vendor).filter(
        Vendor.org_id == ctx.org_id, Vendor.code == payload.code
    ).first():
        raise HTTPException(status_code=409, detail="Vendor code already exists")
    vendor = Vendor(
        org_id=ctx.org_id,
        code=payload.code,
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
        default_terms_days=payload.default_terms_days,
        currency=payload.currency,
        is_1099=payload.is_1099,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return VendorOut.model_validate(vendor)
