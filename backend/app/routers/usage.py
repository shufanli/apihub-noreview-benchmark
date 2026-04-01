"""Usage routes: summary, chart, logs."""
from fastapi import APIRouter, Request, Query
from ..database import get_db
from ..auth import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/usage", tags=["usage"])

PLAN_LIMITS = {
    "free": 1000,
    "pro": 50000,
    "enterprise": 500000,
}


@router.get("/summary")
async def usage_summary(request: Request):
    user = get_current_user(request)
    user_id = user["sub"]
    now = datetime.utcnow()
    today_start = now.strftime("%Y-%m-%d 00:00:00")
    yesterday_start = (now - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    yesterday_end = (now - timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
    month_start = now.strftime("%Y-%m-01 00:00:00")

    with get_db() as conn:
        # Today's calls
        today_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE user_id = ? AND created_at >= ?",
            (user_id, today_start),
        ).fetchone()["cnt"]

        # Yesterday's calls
        yesterday_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE user_id = ? AND created_at >= ? AND created_at <= ?",
            (user_id, yesterday_start, yesterday_end),
        ).fetchone()["cnt"]

        # Monthly calls
        month_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE user_id = ? AND created_at >= ?",
            (user_id, month_start),
        ).fetchone()["cnt"]

        # User plan
        plan_row = conn.execute("SELECT plan FROM users WHERE id = ?", (user_id,)).fetchone()
        plan = plan_row["plan"] if plan_row else "free"

    limit = PLAN_LIMITS.get(plan, 1000)
    change_pct = 0
    if yesterday_count > 0:
        change_pct = round((today_count - yesterday_count) / yesterday_count * 100, 1)

    return {
        "today_calls": today_count,
        "yesterday_calls": yesterday_count,
        "change_pct": change_pct,
        "month_calls": month_count,
        "month_limit": limit,
        "plan": plan,
    }


@router.get("/chart")
async def usage_chart(request: Request, time_range: str = Query("7d", alias="range", pattern="^(7d|30d|90d)$")):
    user = get_current_user(request)
    user_id = user["sub"]
    days = {"7d": 7, "30d": 30, "90d": 90}[time_range]
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d 00:00:00")

    with get_db() as conn:
        rows = conn.execute(
            """SELECT date(created_at) as date, COUNT(*) as count
               FROM usage_logs WHERE user_id = ? AND created_at >= ?
               GROUP BY date(created_at) ORDER BY date""",
            (user_id, start),
        ).fetchall()

    # Fill in missing dates
    result = []
    current = datetime.utcnow() - timedelta(days=days - 1)
    date_map = {r["date"]: r["count"] for r in rows}
    for i in range(days):
        d = (current + timedelta(days=i)).strftime("%Y-%m-%d")
        result.append({"date": d, "count": date_map.get(d, 0)})

    return result


@router.get("/logs")
async def usage_logs(
    request: Request,
    page: int = Query(1, ge=1),
    status: str = Query("all"),
    search: str = Query(""),
):
    user = get_current_user(request)
    user_id = user["sub"]
    per_page = 20
    offset = (page - 1) * per_page

    with get_db() as conn:
        where = "WHERE user_id = ?"
        params: list = [user_id]

        if status != "all":
            try:
                status_code = int(status)
                where += " AND status_code = ?"
                params.append(status_code)
            except ValueError:
                # Filter by status class like "2xx"
                if len(status) == 3 and status.endswith("xx"):
                    prefix = status[0]
                    where += " AND CAST(status_code / 100 AS INTEGER) = ?"
                    params.append(int(prefix))

        if search:
            where += " AND endpoint LIKE ?"
            params.append(f"%{search}%")

        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM usage_logs {where}", params
        ).fetchone()["cnt"]

        rows = conn.execute(
            f"SELECT id, endpoint, status_code, latency_ms, created_at FROM usage_logs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }
