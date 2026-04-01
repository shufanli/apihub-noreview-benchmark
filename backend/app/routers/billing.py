"""Billing routes: current plan, checkout, downgrade, invoices, webhook."""
import os
import uuid
import stripe
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_demo")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_demo")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

PLANS = {
    "free": {"name": "Free", "price_monthly": 0, "price_yearly": 0, "limit": 1000, "stripe_price_monthly": None, "stripe_price_yearly": None},
    "pro": {"name": "Pro", "price_monthly": 2900, "price_yearly": 28800, "limit": 50000, "stripe_price_monthly": "price_pro_monthly", "stripe_price_yearly": "price_pro_yearly"},
    "enterprise": {"name": "Enterprise", "price_monthly": 19900, "price_yearly": 199200, "limit": 500000, "stripe_price_monthly": "price_ent_monthly", "stripe_price_yearly": "price_ent_yearly"},
}


class CheckoutRequest(BaseModel):
    plan: str
    billing_cycle: str = "monthly"


class DowngradeRequest(BaseModel):
    plan: str


@router.get("/current")
async def current_plan(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT plan, stripe_customer_id FROM users WHERE id = ?",
            (user["sub"],),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        plan = row["plan"]
        plan_info = PLANS.get(plan, PLANS["free"])

        # Get usage for this month
        month_usage = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE user_id = ? AND created_at >= date('now', 'start of month')",
            (user["sub"],),
        ).fetchone()["cnt"]

    return {
        "plan": plan,
        "plan_name": plan_info["name"],
        "price_monthly": plan_info["price_monthly"],
        "limit": plan_info["limit"],
        "usage": month_usage,
        "stripe_customer_id": row["stripe_customer_id"],
    }


@router.post("/checkout")
async def create_checkout(body: CheckoutRequest, request: Request):
    user = get_current_user(request)
    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if body.plan == "free":
        raise HTTPException(status_code=400, detail="Cannot checkout for free plan")

    plan_info = PLANS[body.plan]
    price_key = f"stripe_price_{body.billing_cycle}"
    stripe_price = plan_info.get(price_key)

    if not stripe_price:
        raise HTTPException(status_code=400, detail="Invalid billing cycle")

    # In demo mode, return a mock checkout URL
    if stripe.api_key == "sk_test_demo":
        return {
            "checkout_url": f"{FRONTEND_URL}/dashboard/billing?success=true&plan={body.plan}",
            "session_id": f"cs_demo_{uuid.uuid4().hex[:12]}",
        }

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": stripe_price, "quantity": 1}],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/dashboard/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/dashboard/billing?canceled=true",
            metadata={"user_id": user["sub"], "plan": body.plan},
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/downgrade")
async def downgrade(body: DowngradeRequest, request: Request):
    user = get_current_user(request)
    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    with get_db() as conn:
        current = conn.execute("SELECT plan FROM users WHERE id = ?", (user["sub"],)).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="User not found")

        plan_order = {"free": 0, "pro": 1, "enterprise": 2}
        if plan_order.get(body.plan, 0) >= plan_order.get(current["plan"], 0):
            raise HTTPException(status_code=400, detail="Can only downgrade to a lower plan")

        conn.execute("UPDATE users SET plan = ? WHERE id = ?", (body.plan, user["sub"]))

    return {"ok": True, "new_plan": body.plan, "effective": "end_of_current_period"}


@router.get("/invoices")
async def list_invoices(request: Request, page: int = Query(1, ge=1)):
    user = get_current_user(request)
    per_page = 10
    offset = (page - 1) * per_page

    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM invoices WHERE user_id = ?", (user["sub"],)
        ).fetchone()["cnt"]

        rows = conn.execute(
            "SELECT id, amount_cents, status, pdf_url, created_at FROM invoices WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user["sub"], per_page, offset),
        ).fetchall()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if STRIPE_WEBHOOK_SECRET == "whsec_demo":
        return {"ok": True, "demo": True}

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan")
        if user_id and plan:
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET plan = ?, stripe_customer_id = ? WHERE id = ?",
                    (plan, session.get("customer"), user_id),
                )
                conn.execute(
                    "INSERT INTO invoices (id, user_id, amount_cents, status, pdf_url) VALUES (?, ?, ?, ?, ?)",
                    (f"inv_{uuid.uuid4().hex[:8]}", user_id, session.get("amount_total", 0), "paid", ""),
                )

    return {"ok": True}
