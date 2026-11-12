"""Deterministic, user-specific role ranking."""

from datetime import datetime, timezone


def _hit(text, terms):
    return any(term in text for term in terms)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def score_job(job, now=None):
    title = (job.get("title") or "").casefold()
    body = (job.get("_scoring_evidence") or job.get("description_excerpt") or job.get("description") or "").casefold()
    text = f"{title} {body}"

    hands_on = 20 if _hit(text, ("engineer", "builder", "hands-on", "implement", "deploy", "coding", "prototype")) else 6
    ai_cloud = 20 if _hit(text, (" ai ", "artificial intelligence", "agent", "rag", "machine learning", "cloud", "llm")) else 6
    architecture = 15 if _hit(text, ("architect", "architecture", "solution design", "technical design")) else 4
    customers = 15 if _hit(text, ("customer", "client", "forward deployed", "consultant", "field", "workshop")) else 3

    skill_groups = (
        ("c#", ".net"),
        ("python", "typescript", "javascript"),
        ("azure", "openai", "copilot"),
        ("agent", "rag", "retrieval", "search", "evaluation"),
        ("distributed", "kubernetes", "terraform", "container"),
    )
    profile_skills = sum(3 for group in skill_groups if _hit(text, group))

    sponsorship = job.get("sponsorship_status", "unknown")
    sponsorship_points = {
        "explicit_sponsorship": 10,
        "relocation_support": 8,
        "employer_work_permit": 6,
        "unknown": 3,
        "explicit_no_sponsorship": 0,
    }.get(sponsorship, 3)

    freshness = 2 if job.get("source_status") == "official" else 0
    posted = _parse_date(job.get("posted_at"))
    current = _parse_date(now) if isinstance(now, str) else (now or datetime.now(timezone.utc))
    if posted:
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        days = max(0, (current - posted).days)
        freshness += 3 if days <= 14 else (2 if days <= 45 else 1)

    breakdown = {
        "hands_on_engineering": hands_on,
        "ai_cloud": ai_cloud,
        "architecture": architecture,
        "customer_delivery": customers,
        "profile_skills": profile_skills,
        "sponsorship": sponsorship_points,
        "freshness_source": freshness,
    }
    return {
        "total": min(100, sum(breakdown.values())),
        "breakdown": breakdown,
        "sponsorship_red_flag": sponsorship == "explicit_no_sponsorship",
        "compensation_status": "explicit_posted" if job.get("compensation") else "not_posted",
    }
