"""Seed test data for development."""
import uuid
import hashlib
import json
import random
from datetime import datetime, timedelta
from .database import get_db


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def seed_data():
    with get_db() as conn:
        # Check if already seeded
        row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        if row["cnt"] > 0:
            return

        # Users
        user1_id = "user_pro_001"
        user2_id = "user_free_002"

        conn.execute(
            "INSERT INTO users (id, github_id, username, email, avatar_url, plan, stripe_customer_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user1_id, 12345, "alice-dev", "alice@example.com", "https://avatars.githubusercontent.com/u/12345", "pro", "cus_test_alice"),
        )
        conn.execute(
            "INSERT INTO users (id, github_id, username, email, avatar_url, plan) VALUES (?, ?, ?, ?, ?, ?)",
            (user2_id, 67890, "bob-builder", "bob@example.com", "https://avatars.githubusercontent.com/u/67890", "free"),
        )

        # API Keys
        keys = [
            ("key_001", user1_id, "Production Key", "Main production API key", "ah_prod_abc", '["read","write","admin"]'),
            ("key_002", user1_id, "Staging Key", "For staging env", "ah_stag_def", '["read","write"]'),
            ("key_003", user2_id, "Test Key", "Testing purposes", "ah_test_ghi", '["read"]'),
        ]
        for kid, uid, name, desc, prefix, perms in keys:
            conn.execute(
                "INSERT INTO api_keys (id, user_id, name, description, key_hash, key_prefix, permissions) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (kid, uid, name, desc, hash_key(f"full_key_{kid}"), prefix, perms),
            )

        # Usage logs - 90 days, ~120 records
        endpoints = ["/api/v1/data", "/api/v1/users", "/api/v1/search", "/api/v1/upload", "/api/v1/analytics"]
        statuses = [200, 200, 200, 200, 200, 201, 400, 401, 404, 500]  # Weighted towards 2xx
        now = datetime.utcnow()

        for i in range(120):
            days_ago = random.randint(0, 89)
            hours = random.randint(0, 23)
            minutes = random.randint(0, 59)
            ts = now - timedelta(days=days_ago, hours=hours, minutes=minutes)
            user_id = random.choice([user1_id, user2_id])
            endpoint = random.choice(endpoints)
            status = random.choice(statuses)
            latency = random.randint(12, 850)

            conn.execute(
                "INSERT INTO usage_logs (user_id, endpoint, status_code, latency_ms, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, endpoint, status, latency, ts.strftime("%Y-%m-%d %H:%M:%S")),
            )

        # Invoices - 12 months
        for i in range(12):
            month_date = now - timedelta(days=30 * (11 - i))
            inv_id = f"inv_{uuid.uuid4().hex[:8]}"
            user_id = user1_id if i % 3 != 2 else user2_id
            amount = 2900 if user_id == user1_id else 0
            status = "paid" if i < 11 else "pending"

            conn.execute(
                "INSERT INTO invoices (id, user_id, amount_cents, status, pdf_url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (inv_id, user_id, amount, status, f"https://stripe.com/invoice/{inv_id}/pdf", month_date.strftime("%Y-%m-%d %H:%M:%S")),
            )
