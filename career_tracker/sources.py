"""HTTP clients for official public career feeds (stdlib only)."""

import json
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


def fetch_source(spec, opener=None):
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
    raise ValueError(f"Unsupported source kind: {kind}")
