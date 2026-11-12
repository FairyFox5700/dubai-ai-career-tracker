"""Safe spreadsheet-friendly CSV export."""

import csv
import io
from urllib.parse import urlparse

FIELDS = (
    "company", "title", "location", "score", "sponsorship_status", "source_status", "open_status",
    "compensation", "raw_application_url", "application_link_clickable",
)


def _safe_text(value):
    value = "" if value is None else str(value)
    if value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _https_url(value):
    try:
        parsed = urlparse(value or "")
    except (TypeError, ValueError):
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _compensation(value):
    if not value:
        return "Not posted"
    return f"{value.get('currency')} {value.get('min'):,}–{value.get('max'):,} / {value.get('period', 'unspecified')} (official posting)"


def jobs_csv(jobs):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for job in jobs:
        url = str(job.get("url") or "")
        formula = ""
        if _https_url(url):
            escaped = url.replace('"', '""')
            label = "Open LinkedIn discovery" if job.get("source_status") == "linkedin_discovery" else "Open official posting"
            formula = f'=HYPERLINK("{escaped}","{label}")'
        writer.writerow({
            "company": _safe_text(job.get("company")),
            "title": _safe_text(job.get("title")),
            "location": _safe_text(job.get("location")),
            "score": job.get("score", {}).get("total", ""),
            "sponsorship_status": _safe_text(job.get("sponsorship_status")),
            "source_status": _safe_text(job.get("source_status") or "official"),
            "open_status": _safe_text(job.get("open_status")),
            "compensation": _safe_text(_compensation(job.get("compensation"))),
            "raw_application_url": url,
            "application_link_clickable": formula,
        })
    return output.getvalue()
