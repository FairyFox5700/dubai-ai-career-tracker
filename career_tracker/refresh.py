"""Isolated source refresh and artifact generation."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .adapters import normalize_amazon, normalize_ashby, normalize_greenhouse, normalize_lever, normalize_workday
from .export import jobs_csv
from .scoring import score_job
from .sources import fetch_source


def _timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_jobs(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("jobs", [])
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="")
    os.replace(temporary, path)


def _atomic_json(path, payload):
    _atomic_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _normalize(spec, payload):
    company, kind = spec["company"], spec["kind"]
    if kind == "greenhouse":
        return normalize_greenhouse(payload, company)
    if kind == "ashby":
        return normalize_ashby(payload, company)
    if kind == "lever":
        return normalize_lever(payload, company)
    if kind == "amazon":
        return normalize_amazon(payload, company)
    if kind == "workday":
        base_url = spec.get("base_url") or f"https://{spec['host']}/{spec['site']}"
        return normalize_workday(payload, company, base_url)
    raise ValueError(f"Unsupported source kind: {kind}")


def refresh(specs, data_path, report_path, csv_path, fetcher=fetch_source, now=None):
    generated_at = now or _timestamp()
    previous = _read_jobs(data_path)
    jobs = []
    sources_ok, sources_failed, source_results = [], [], []

    for spec in specs:
        company = spec["company"]
        try:
            normalized = _normalize(spec, fetcher(spec))
            jobs.extend(normalized)
            sources_ok.append(company)
            source_results.append({"company": company, "kind": spec["kind"], "status": "ok", "live_jobs": len(normalized)})
        except Exception as exc:  # Isolation is intentional: source failures must not erase known roles.
            preserved = []
            for old in previous:
                if old.get("company") == company:
                    old = dict(old)
                    old["stale"] = True
                    old["source_status"] = "source_error"
                    old["open_status"] = "source_error"
                    old["stale_reason"] = f"{type(exc).__name__}: {exc}"[:300]
                    preserved.append(old)
            jobs.extend(preserved)
            sources_failed.append(company)
            source_results.append({
                "company": company, "kind": spec["kind"], "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:500], "jobs_preserved": len(preserved),
            })

    deduped = {}
    for job in jobs:
        key = (job.get("company", "").casefold(), job.get("title", "").casefold(), job.get("location", "").casefold(), job.get("source_id", ""))
        deduped[key] = job
    jobs = list(deduped.values())
    for job in jobs:
        job["score"] = score_job(job, now=generated_at)
    jobs.sort(key=lambda item: (-item["score"]["total"], item.get("company", ""), item.get("title", ""), item.get("source_id", "")))

    live_jobs = [job for job in jobs if not job.get("stale") and job.get("open_status") == "verified_open"]
    data = {"generated_at": generated_at, "live_job_count": len(live_jobs), "total_with_stale": len(jobs), "jobs": jobs}
    report = {
        "generated_at": generated_at,
        "live_job_count": len(live_jobs),
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "sources": source_results,
    }
    _atomic_json(data_path, data)
    _atomic_json(report_path, report)
    _atomic_text(csv_path, jobs_csv(jobs))
    return report
