"""HTTP clients for official public career feeds (stdlib only)."""

import json
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

USER_AGENT = "DubaiAICareerTracker/1.0 (+public official career sources only)"


def _json_request(url, opener, data=None):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with opener(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def _text_request(url, opener):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with opener(request, timeout=40) as response:
        return response.read().decode("utf-8", errors="replace")


def _workday(spec, opener):
    root = f"https://{spec['host']}/wday/cxs/{spec['tenant']}/{spec['site']}"
    search_url = root + "/jobs"
    postings = []
    offset = 0
    while True:
        body = json.dumps({
            "appliedFacets": {},
            "limit": 20,
            "offset": offset,
            "searchText": spec.get("search_text", "Dubai"),
        }).encode("utf-8")
        page = _json_request(search_url, opener, data=body)
        batch = page.get("jobPostings", [])
        postings.extend(batch)
        offset += len(batch)
        if not batch or offset >= int(page.get("total", len(postings))):
            break

    verified = []
    for summary in postings:
        path = summary.get("externalPath")
        if not path:
            continue
        detail = _json_request(root + "/" + path.lstrip("/"), opener).get("jobPostingInfo", {})
        if detail.get("canApply") is False:
            continue
        merged = dict(summary)
        merged.update({
            "jobReqId": detail.get("jobReqId") or summary.get("jobReqId"),
            "jobPostingId": detail.get("jobPostingId"),
            "jobDescription": detail.get("jobDescription") or "",
            "location": detail.get("location") or summary.get("locationsText"),
            "postedAt": detail.get("startDate") or detail.get("postedOn"),
            "canApply": detail.get("canApply", True),
        })
        verified.append(merged)
    return {"jobPostings": verified}


def fetch_source(spec, opener=None, sleeper=time.sleep):
    opener = opener or urlopen
    kind = spec["kind"]
    if kind == "greenhouse":
        return _json_request(f"https://boards-api.greenhouse.io/v1/boards/{quote(spec['board'])}/jobs?content=true", opener)
    if kind == "ashby":
        return _json_request(f"https://api.ashbyhq.com/posting-api/job-board/{quote(spec['board'])}", opener)
    if kind == "lever":
        return _json_request(f"https://api.lever.co/v0/postings/{quote(spec['site'])}?mode=json", opener)
    if kind == "amazon":
        query = urlencode({"base_query": spec.get("query", "Dubai"), "result_limit": 100})
        return _json_request(f"https://www.amazon.jobs/en/search.json?{query}", opener)
    if kind == "workday":
        return _workday(spec, opener)
    if kind == "smartrecruiters":
        company_id = quote(spec["company_id"])
        root = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
        postings = []
        offset, limit = 0, 100
        while True:
            page = _json_request(root + "?" + urlencode({"limit": limit, "offset": offset}), opener)
            batch = page.get("content", [])
            postings.extend(batch)
            offset += len(batch)
            if not batch or offset >= int(page.get("totalFound", len(postings))):
                break
        enriched = []
        for summary in postings:
            detail = _json_request(root + "/" + quote(str(summary.get("id"))), opener)
            merged = dict(summary)
            merged.update(detail)
            enriched.append(merged)
        return {"content": enriched}
    if kind == "oracle":
        finder = ";".join((
            "findReqs",
            f"siteNumber={spec['site']}",
            f"limit={int(spec.get('limit', 100))}",
            "offset=0",
            f"location={spec.get('location', 'United Arab Emirates')}",
        ))
        query = urlencode({"onlyData": "true", "finder": finder, "expand": "requisitionList"})
        search = _json_request(spec["base_url"] + "?" + query, opener)
        summaries = (search.get("items") or [{}])[0].get("requisitionList", [])
        details_url = spec.get("details_url") or spec["base_url"].replace("recruitingCEJobRequisitions", "recruitingCEJobRequisitionDetails")
        enriched = []
        for summary in summaries:
            detail_query = urlencode({
                "onlyData": "true",
                "finder": f"ById;Id={summary.get('Id')},siteNumber={spec['site']}",
            })
            detail_page = _json_request(details_url + "?" + detail_query, opener)
            detail = (detail_page.get("items") or [{}])[0]
            merged = dict(summary)
            merged.update(detail)
            enriched.append(merged)
        return {"items": enriched}
    if kind == "linkedin":
        pages = max(1, min(int(spec.get("pages", 2)), 3))
        queries = list(spec.get("queries") or [])[:10]
        delay = max(0.0, min(float(spec.get("delay_seconds", 1.0)), 10.0))
        chunks = []
        attempts = [(query, page * 25) for query in queries for page in range(pages)]
        for index, (query, start) in enumerate(attempts):
            url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urlencode({
                "keywords": query, "location": spec.get("location", "Dubai, United Arab Emirates"),
                "start": start,
            })
            try:
                chunks.append(_text_request(url, opener))
            except Exception:
                pass
            if index + 1 < len(attempts):
                sleeper(delay)
        if attempts and not chunks:
            raise RuntimeError("all LinkedIn guest search requests failed")
        return "\n".join(chunks)
    raise ValueError(f"Unsupported source kind: {kind}")
