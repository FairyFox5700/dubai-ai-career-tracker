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


def classify_role(title, description=""):
    """Classify a role from its complete description before public truncation."""
    title = clean_text(title)
    evidence = clean_text(description)
    title_cf = title.casefold()
    combined = f"{title} {evidence}".casefold()
    rejected = {"eligible": False, "role_family": None}

    if EXCLUDED_SENIORITY.search(title):
        return {**rejected, "match_reason": "excluded staff/principal seniority"}
    if re.search(r"\b(?:graduate|apprentice(?:ship)?|intern(?:ship)?|junior|entry[- ]level)\b", title, re.I):
        return {**rejected, "match_reason": "excluded early-career role"}
    if not ALLOWED_SENIORITY.search(title):
        return {**rejected, "match_reason": "missing target seniority"}

    arabic_required = re.search(
        r"(?:arabic.{0,35}\b(?:required|mandatory|must|fluen(?:t|cy)|native)\b|"
        r"\b(?:required|mandatory|must|fluen(?:t|cy)|native).{0,35}arabic\b)",
        combined,
        re.I,
    )
    arabic_optional = re.search(r"arabic.{0,30}(?:preferred|nice[- ]to[- ]have|advantage|plus)", combined, re.I)
    if EXCLUDED_LANGUAGE_REQUIREMENT.search(title) or (arabic_required and not arabic_optional):
        return {**rejected, "match_reason": "Arabic is a hard requirement"}

    exact_tam = bool(re.fullmatch(r"senior technical account manager", title_cf))
    people_manager = bool(
        (re.search(r"\b(?:senior|sr\.?|snr|lead) manager\b", title, re.I) and not exact_tam)
        or re.search(
            r"\b(?:people management|manage(?:s|ment|ing)? (?:a |the )?team|lead(?:ing)? a team of|"
            r"direct reports?|performance reviews?|hiring and developing)\b",
            combined,
            re.I,
        )
    )
    if people_manager:
        return {**rejected, "match_reason": "explicit people-management role"}

    ai_signal = bool(re.search(r"\b(?:ai|a\.i\.|ml|machine learning|genai|generative ai|agentic ai|llm|rag)\b", combined, re.I))
    customer_signal = bool(re.search(r"\b(?:customers?|clients?|professional services|consulting|delivery|implementation|workshop|presales|pre-sales)\b", combined, re.I))

    families = (
        ("forward_deployed_ai", r"\bforward deployed(?: ai| software)? engineer\b", True),
        ("ai_platform_engineering", r"\b(?:ai|ai/ml|ml) (?:platform|infrastructure) engineer\b", False),
        ("ai_systems_engineering", r"\bai systems engineer\b", False),
        ("ai_implementation", r"\bai implementation engineer\b", False),
        ("ai_integration_architecture", r"\bintegration architect\b", True),
        ("professional_services", r"\bprofessional services (?:engineer|consultant|architect)\b", True),
        ("customer_success", r"\bcustomer success (?:architect|engineer)\b", True),
        ("solutions_consulting", r"\bsolutions? consultant\b", True),
        ("technical_account_management", r"^senior technical account manager$", False),
        ("technical_architecture", r"\btechnical architect\b", True),
        ("ai_architecture", r"\b(?:(?:data\s*(?:&|and)\s*ai|enterprise ai|genai|generative ai|agentic ai|ai platform|ai|cloud)\s+architect|architect[^.]{0,40}\b(?:ai|genai|agentic ai))\b", False),
        ("customer_engineering", r"\b(?:ai |cloud )?customer engineer\b", False),
        ("solutions_architecture", r"\bsolutions? architect\b", False),
        ("solutions_engineering", r"\b(?:lead )?solutions? engineer\b", False),
        ("delivery_architecture", r"\bdelivery architect\b", False),
        ("technical_lead", r"\btechnical lead\b", True),
        ("applied_ai", r"\bapplied (?:ai|value) (?:engineer|architect)\b", False),
        ("deployment_engineering", r"\b(?:field|deployment) engineer\b", True),
        ("technical_consulting", r"\btechnical consultant\b", True),
    )
    for family, pattern, needs_evidence in families:
        if re.search(pattern, title, re.I) and (not needs_evidence or ai_signal or customer_signal):
            details = []
            if customer_signal:
                details.append("customer-delivery")
            if ai_signal:
                details.append("AI")
            suffix = f" with {' and '.join(details)} evidence" if details else ""
            return {"eligible": True, "role_family": family, "match_reason": family.replace("_", " ") + suffix}

    generic_ml = re.search(r"\b(?:machine learning|ml) engineer\b", title, re.I)
    if generic_ml and ai_signal and customer_signal:
        return {"eligible": True, "role_family": "customer_ml_engineering", "match_reason": "ML engineering with customer-delivery evidence"}

    production_ai = bool(re.search(r"\b(?:build|ship|deploy|production|coding|python|llm|generative ai|evaluation|monitor)\w*\b", evidence, re.I))
    if re.search(r"\bdata scientist\b", title, re.I) and ai_signal and production_ai:
        return {
            "eligible": True,
            "role_family": "production_ai_data_science",
            "match_reason": "AI data science with hands-on production building evidence",
        }

    return {**rejected, "match_reason": "title lacks safe target-role evidence"}


def title_is_target(title):
    return classify_role(title).get("eligible", False)


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


def _base(company, source, source_id, title, location, url, posted_at, description, url_hint="", source_status="official", open_status="verified_open"):
    status, evidence = sponsorship_evidence(description)
    if status == "unknown":
        evidence = "UAE employment normally uses an employer-sponsored work-permit and residence-visa pathway; this listing does not state the employer's sponsorship commitment."
        status = "employer_work_permit"
    classification = classify_role(title, description)
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
        "_scoring_evidence": description,
        "role_family": classification["role_family"],
        "match_reason": classification["match_reason"],
        "sponsorship_status": status,
        "sponsorship_evidence": evidence,
        "compensation": compensation(description),
        "source": source,
        "source_status": source_status,
        "open_status": open_status,
        "stale": False,
    }


def _eligible(title, location, hint="", description=""):
    return classify_role(title, description)["eligible"] and location_is_dubai(location, hint)


def normalize_greenhouse(payload, company):
    jobs = []
    for raw in payload.get("jobs", []):
        title = raw.get("title")
        location = (raw.get("location") or {}).get("name", "")
        for field in raw.get("metadata") or []:
            if (field.get("name") or "").casefold() == "job posting location":
                values = field.get("value") or []
                if isinstance(values, str):
                    values = [values]
                explicit = ", ".join(str(value) for value in values)
                if explicit:
                    location = explicit
        description = raw.get("content", "")
        if _eligible(title, location, raw.get("absolute_url", ""), description):
            jobs.append(_base(company, "greenhouse", raw.get("id"), title, location, raw.get("absolute_url"), raw.get("updated_at"), description))
    return jobs


def normalize_ashby(payload, company):
    jobs = []
    for raw in payload.get("jobs", []):
        title, location = raw.get("title"), raw.get("location", "")
        url = raw.get("jobUrl") or raw.get("applyUrl")
        description = raw.get("descriptionPlain") or raw.get("descriptionHtml") or ""
        if _eligible(title, location, url, description):
            jobs.append(_base(company, "ashby", raw.get("id"), title, location, url, raw.get("publishedAt"), description))
    return jobs


def normalize_lever(payload, company):
    jobs = []
    for raw in payload:
        title = raw.get("text") or raw.get("title")
        location = (raw.get("categories") or {}).get("location", "")
        url = raw.get("hostedUrl") or raw.get("applyUrl")
        description = raw.get("descriptionPlain") or raw.get("description") or ""
        if _eligible(title, location, url, description):
            jobs.append(_base(company, "lever", raw.get("id"), title, location, url, raw.get("createdAt"), description))
    return jobs


def normalize_amazon(payload, company):
    jobs = []
    for raw in payload.get("jobs", []):
        title, location = raw.get("title"), raw.get("location", "")
        path = raw.get("job_path", "")
        url = urljoin("https://www.amazon.jobs", path)
        description = " ".join(str(raw.get(key) or "") for key in ("description", "basic_qualifications", "preferred_qualifications"))
        if _eligible(title, location, path, description):
            jobs.append(_base(company, "amazon_jobs", raw.get("id_icims") or raw.get("id"), title, location, url, raw.get("posted_date"), description, path))
    return jobs


def normalize_workday(payload, company, base_url):
    jobs = []
    for raw in payload.get("jobPostings", []):
        title = raw.get("title")
        path = raw.get("externalPath", "")
        location = raw.get("locationsText") or raw.get("location") or ""
        description = raw.get("jobDescription") or ""
        if _eligible(title, location, path, description):
            source_id = raw.get("jobReqId") or raw.get("jobPostingId") or path.rsplit("_", 1)[-1]
            jobs.append(_base(company, "workday", source_id, title, location, urljoin(base_url.rstrip("/") + "/", path.lstrip("/")), raw.get("postedAt") or raw.get("startDate"), description, path))
    return jobs


def normalize_smartrecruiters(payload, company):
    jobs = []
    for raw in payload.get("content", []):
        title = raw.get("name") or raw.get("title")
        place = raw.get("location") or {}
        location = ", ".join(part for part in (place.get("city"), place.get("country")) if part)
        url = raw.get("ref") or raw.get("applyUrl") or raw.get("url")
        sections = ((raw.get("jobAd") or {}).get("sections") or {})
        description = " ".join(
            clean_text((section or {}).get("text", ""))
            for section in sections.values()
            if isinstance(section, dict)
        )
        if _eligible(title, location, url, description):
            jobs.append(_base(company, "smartrecruiters", raw.get("id"), title, location, url, raw.get("releasedDate"), description))
    return jobs


def normalize_oracle(payload, company):
    jobs = []
    for raw in payload.get("items", []):
        title = raw.get("Title") or raw.get("title")
        location = raw.get("PrimaryLocation") or raw.get("Location") or raw.get("primaryLocation") or ""
        description = " ".join(str(raw.get(key) or "") for key in (
            "ExternalDescriptionStr", "ExternalJobDescriptionStr", "ShortDescriptionStr",
            "ExternalResponsibilitiesStr", "ExternalQualificationsStr",
        ))
        source_id = raw.get("JobId") or raw.get("Id")
        url = raw.get("ExternalCareerSiteUrl") or f"https://careers.oracle.com/jobs/#en/sites/jobsearch/job/{source_id}"
        if _eligible(title, location, url, description):
            jobs.append(_base(company, "oracle_recruiting", source_id, title, location, url, raw.get("PostedDate"), description))
    return jobs


def _class_text(chunk, class_name):
    match = re.search(
        rf'<[^>]+class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>(.*?)</[^>]+>',
        chunk,
        re.I | re.S,
    )
    return clean_text(match.group(1)) if match else ""


def normalize_linkedin(payload, company=None):
    """Normalize public guest-search cards as unverified discovery records."""
    jobs = []
    starts = list(re.finditer(r'data-entity-urn=["\']urn:li:jobPosting:(\d+)["\']', payload or "", re.I))
    for index, match in enumerate(starts):
        chunk = payload[match.start(): starts[index + 1].start() if index + 1 < len(starts) else len(payload)]
        source_id = match.group(1)
        title = _class_text(chunk, "base-search-card__title")
        discovered_company = _class_text(chunk, "base-search-card__subtitle")
        location = _class_text(chunk, "job-search-card__location")
        href = re.search(r'class=["\'][^"\']*base-card__full-link[^"\']*["\'][^>]+href=["\']([^"\']+)', chunk, re.I)
        posted = re.search(r'<time[^>]+datetime=["\']([^"\']+)', chunk, re.I)
        url = html.unescape(href.group(1)) if href else f"https://www.linkedin.com/jobs/view/{source_id}"
        explicit_ai = re.search(
            r"\b(?:ai|a\.i\.|ml|machine learning|genai|generative ai|agentic|forward deployed|applied value)\b",
            title,
            re.I,
        )
        language_market = re.search(r"\b\w+ speaking\b", title, re.I)
        if explicit_ai and not language_market and _eligible(title, location, url, title):
            job = _base(
                "LinkedIn", "linkedin_guest", source_id, title, location, url,
                posted.group(1) if posted else None, title,
                source_status="linkedin_discovery", open_status="linkedin_active",
            )
            job["company"] = discovered_company or company or "Unknown company"
            jobs.append(job)
    return jobs
