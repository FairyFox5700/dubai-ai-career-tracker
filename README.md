# Dubai AI Career Tracker

A Dubai-only, local-first tracker for Iryna Tyshchenko's move from Software Engineer II / AI Engineer at Microsoft Dublin into senior, lead, or architect-level customer-facing AI delivery roles. The dashboard combines verified-open roles from official public career feeds, clearly labeled discovery from LinkedIn's public guest search, and a practical UAE sponsorship strategy.

This is a static, local-first GitHub Pages tracker. It has no analytics, backend, secrets, or third-party Python packages; personal pipeline statuses remain only in the browser.

## Run locally

Python 3.11+ is sufficient.

```bash
python scripts/refresh.py
python -m http.server 8765
```

Open <http://localhost:8765>. Opening `index.html` from `file://` will not work because browsers block its JSON fetches.

## Verify

```bash
python -m unittest discover -s tests -v
python -m compileall -q career_tracker scripts
```

## Scope and evidence rules

- **Location:** Dubai is a hard filter. A UAE-remote posting is accepted only when its official location explicitly covers the UAE and therefore Dubai. Abu Dhabi-only roles are excluded.
- **Seniority:** keeps Senior, Sr., Snr, Lead, and Architect; excludes Staff and Principal even when the title also contains Lead.
- **Role family:** explicit senior AI delivery families include Forward Deployed, AI platform/systems/implementation, Applied AI/Value, Customer/Field/Success, Solutions/Delivery/Integration/Technical Architect, Professional Services, Solutions Consulting, and the exact Senior Technical Account Manager exception. Generic software, cloud, data, ML, consulting, and architecture titles still require explicit AI or customer-delivery evidence.
- **Exclusions:** Staff and Principal always fail. Explicit people-management patterns fail except the exact Senior Technical Account Manager title. Arabic required/native/fluent/mandatory fails from the full description; Arabic preferred or nice-to-have does not.
- **Open status:** official records are `verified_open`; LinkedIn guest cards are `linkedin_active` discovery only. LinkedIn is never represented as official verification. HTTP 200 alone is not enough; Workday detail records must remain applyable.
- **Compensation:** only explicit AED or EUR ranges from the official posting are shown. Missing pay stays “Not posted”; there are no estimates.
- **Sponsorship:** listing evidence is classified as explicit sponsorship, relocation support, normal employer-sponsored UAE permit pathway, unknown, or explicit no-sponsorship. The normal UAE pathway is not represented as a promise by a particular employer.
- **Failures:** adapters are isolated. A failed source preserves its prior records as stale/source-error records and excludes them from the live count.

## Official automated sources

- Greenhouse public job-board API: Databricks, Anthropic, Celonis
- Ashby public posting feed: OpenAI
- Lever public posting API: Palantir
- Amazon Jobs official JSON search: AWS
- Workday public career endpoints plus applyability detail checks: Salesforce, NVIDIA
- Workday: Visa
- Greenhouse: Cloudflare, Elastic
- SmartRecruiters: Delivery Hero/talabat
- Oracle Recruiting Cloud: Oracle (UAE search; strict Dubai normalization still applies)
- LinkedIn public guest discovery: six bounded Dubai title queries, two pages per query, delayed between requests, fail-soft, and cross-source deduplicated in favor of official records

SAP had strong official matches during research, but its automated career site was Cloudflare-blocked, so no stale static records were fabricated. Microsoft's only current match was an Emirati-only apprenticeship and was excluded. Google Cloud, IBM, ServiceNow, G42/Core42/Presight, Careem, and Accenture are not configured where a stable public unattended feed could not be verified.

## Dashboard

- Search and filter by company, source confidence, sponsorship evidence, minimum score, and local pipeline status.
- Inspect the full factor breakdown and official evidence excerpt.
- Keep progress in browser `localStorage`: New, Reviewing, Shortlisted, Applied, Interviewing, Offer, Rejected, Withdrawn, or Archived.
- Review per-source health and the latest generation timestamp.
- Export the filtered view to CSV with source status, the raw source URL, and a spreadsheet-clickable `HYPERLINK` formula. Untrusted text is formula-injection protected.
- Read a visible sponsorship strategy covering the employment-visa workflow, target tiers, CV positioning, recruiter questions, red flags, cadence, networking, and offer diligence.

## UAE visa sources

The strategy links to primary public guidance rather than promising eligibility:

- [UAE Government — job offers, work permits and contracts](https://u.ae/en/information-and-services/jobs/employment-in-the-private-sector/job-offers-and-work-permits-and-contracts)
- [UAE Government — preparing to work](https://u.ae/en/information-and-services/jobs/working-in-uae)
- [MOHRE — overseas worker permit service](https://www.mohre.gov.ae/en/services/work-permit-for-recruiting-a-worker-from-outside-the-state-2022)

Re-check the linked government guidance before relying on it; immigration procedures can change.

## Automation

- `ci.yml`: tests and compile check.
- `refresh.yml`: daily official plus LinkedIn-discovery refresh and generated-data commit.
- `pages.yml`: explicit GitHub Pages deployment.

All workflows use GitHub's built-in permissions and current requested action majors. They reference no repository secrets.

## License

MIT — see [LICENSE](LICENSE).
