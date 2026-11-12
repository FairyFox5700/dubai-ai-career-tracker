"""Normalize public ATS records into the Dubai tracker schema."""

import html
import re
from urllib.parse import urljoin

ALLOWED_SENIORITY = re.compile(r"\b(?:senior|sr\.?|snr|lead|architect)\b", re.I)
EXCLUDED_SENIORITY = re.compile(r"\b(?:staff|principal)\b", re.I)
TARGET_ROLE = re.compile(
    r"\b(?:forward deployed(?: software)? engineer|applied (?:ai|value) (?:engineer|architect)|"
    r"(?:ai|cloud) customer engineer|customer engineer|field engineer|deployment engineer|"
    r"solutions? architect|solutions? engineer|delivery architect|technical consultant|"
    r"account cloud engineer|technical account (?:manager|architect)|ai agent technical builder)\b",
    re.I,
)
EXCLUDED_ROLE = re.compile(
    r"\b(?:account executive|sales specialist|sales representative|intern(?:ship)?|manager|director|recruiter)\b",
    re.I,
)
EXCLUDED_LANGUAGE_REQUIREMENT = re.compile(r"\barabic[- ]speaking\b", re.I)


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_is_target(title):
    title = title or ""
    return bool(
        ALLOWED_SENIORITY.search(title)
        and not EXCLUDED_SENIORITY.search(title)
        and TARGET_ROLE.search(title)
        and not EXCLUDED_ROLE.search(title)
        and not EXCLUDED_LANGUAGE_REQUIREMENT.search(title)
    )


def location_is_dubai(location, url_hint=""):
    text = f"{location or ''} {url_hint or ''}".casefold().replace("_", "-")
    if "abu dhabi" in text or "abu-dhabi" in text:
        return False
    if "dubai" in text:
        return True
    return "remote" in text and any(term in text for term in ("united arab emirates", "uae", " ae"))


def canonical_location(location, url_hint=""):
    text = clean_text(location)
    if "remote" in text.casefold():
        return "Remote — United Arab Emirates (Dubai eligible)"
    if "dubai" in f"{text} {url_hint}".casefold():
        return "Dubai, United Arab Emirates"
    return text


def sponsorship_evidence(description):
    text = clean_text(description)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    patterns = (
        ("explicit_no_sponsorship", ("no visa sponsorship", "sponsorship is not available", "cannot provide sponsorship", "unable to sponsor", "does not sponsor")),
        ("explicit_sponsorship", ("visa sponsorship", "sponsorship is available", "sponsor your visa", "sponsor visas")),
        ("relocation_support", ("relocation support", "relocation and immigration", "immigration support", "visa support")),
        ("employer_work_permit", ("employer will arrange", "employment visa and work permit", "employer-sponsored work permit")),
    )
    for status, terms in patterns:
        for sentence in sentences:
            if any(term in sentence.casefold() for term in terms):
                return status, sentence[:260]
    return "unknown", "No explicit sponsorship or relocation language in the official posting."


def compensation(text):
    clean = clean_text(text)
    match = re.search(
        r"\b(?P<currency>AED|EUR)\s*(?P<low>[\d,.]+)\s*(?:-|–|—|to)\s*(?P<high>[\d,.]+)\b",
        clean,
        re.I,
    )
    if not match:
        return None
    return {
        "currency": match.group("currency").upper(),
        "min": int(float(match.group("low").replace(",", ""))),
        "max": int(float(match.group("high").replace(",", ""))),
        "period": "year" if re.search(r"annual|per year|yearly", clean[match.start():match.end() + 40], re.I) else "unspecified",
        "source": "official_posting",
    }


def _base(company, source, source_id, title, location, url, posted_at, description, url_hint=""):
    status, evidence = sponsorship_evidence(description)
    if status == "unknown":
        evidence = "UAE employment normally uses an employer-sponsored work-permit and residence-visa pathway; this listing does not state the employer's sponsorship commitment."
        status = "employer_work_permit"
    description = clean_text(description)
    return {
        "id": f"{company}:{source_id}",
        "source_id": str(source_id),
        "company": company,
        "title": clean_text(title),
        "location": canonical_location(location, url_hint),
        "url": url,
        "posted_at": posted_at,
        "description_excerpt": description[:700],
        "sponsorship_status": status,
        "sponsorship_evidence": evidence,
        "compensation": compensation(description),
        "source": source,
        "source_status": "official",
        "open_status": "verified_open",
        "stale": False,
    }


def _eligible(title, location, hint=""):
    return title_is_target(title) and location_is_dubai(location, hint)


def normalize_greenhouse(payload, company):
    jobs = []
    for raw in payload.get("jobs", []):
        title = raw.get("title")
        location = (raw.get("location") or {}).get("name", "")
        if _eligible(title, location, raw.get("absolute_url", "")):
            jobs.append(_base(company, "greenhouse", raw.get("id"), title, location, raw.get("absolute_url"), raw.get("updated_at"), raw.get("content", "")))
    return jobs


def normalize_ashby(payload, company):
    jobs = []
    for raw in payload.get("jobs", []):
        title, location = raw.get("title"), raw.get("location", "")
        url = raw.get("jobUrl") or raw.get("applyUrl")
        if _eligible(title, location, url):
            jobs.append(_base(company, "ashby", raw.get("id"), title, location, url, raw.get("publishedAt"), raw.get("descriptionPlain") or raw.get("descriptionHtml") or ""))
    return jobs


def normalize_lever(payload, company):
    jobs = []
    for raw in payload:
        title = raw.get("text") or raw.get("title")
        location = (raw.get("categories") or {}).get("location", "")
        url = raw.get("hostedUrl") or raw.get("applyUrl")
        if _eligible(title, location, url):
            jobs.append(_base(company, "lever", raw.get("id"), title, location, url, raw.get("createdAt"), raw.get("descriptionPlain") or raw.get("description") or ""))
    return jobs


def normalize_amazon(payload, company):
    jobs = []
    for raw in payload.get("jobs", []):
        title, location = raw.get("title"), raw.get("location", "")
        path = raw.get("job_path", "")
        url = urljoin("https://www.amazon.jobs", path)
        if _eligible(title, location, path):
            description = " ".join(str(raw.get(key) or "") for key in ("description", "basic_qualifications", "preferred_qualifications"))
            jobs.append(_base(company, "amazon_jobs", raw.get("id_icims") or raw.get("id"), title, location, url, raw.get("posted_date"), description, path))
    return jobs


def normalize_workday(payload, company, base_url):
    jobs = []
    for raw in payload.get("jobPostings", []):
        title = raw.get("title")
        path = raw.get("externalPath", "")
        location = raw.get("locationsText") or raw.get("location") or ""
        if _eligible(title, location, path):
            source_id = raw.get("jobReqId") or raw.get("jobPostingId") or path.rsplit("_", 1)[-1]
            jobs.append(_base(company, "workday", source_id, title, location, urljoin(base_url.rstrip("/") + "/", path.lstrip("/")), raw.get("postedAt") or raw.get("startDate"), raw.get("jobDescription") or "", path))
    return jobs
