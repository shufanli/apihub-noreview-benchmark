"""Pricing route."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/pricing", tags=["pricing"])

PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "limit": 1000,
        "features": [
            "1,000 API calls/month",
            "Basic analytics",
            "Community support",
            "1 API key",
        ],
        "popular": False,
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_monthly": 29,
        "price_yearly": 24,
        "limit": 50000,
        "features": [
            "50,000 API calls/month",
            "Advanced analytics",
            "Priority support",
            "Unlimited API keys",
            "Webhook notifications",
        ],
        "popular": True,
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 166,
        "limit": 500000,
        "features": [
            "500,000 API calls/month",
            "Real-time analytics",
            "Dedicated support",
            "Unlimited API keys",
            "Webhook notifications",
            "Custom endpoints",
            "SLA guarantee",
        ],
        "popular": False,
    },
]


@router.get("")
async def get_pricing():
    return PLANS
