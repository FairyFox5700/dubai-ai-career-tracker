# Dubai AI Career Tracker

A Dubai-only, local-first tracker for Iryna Tyshchenko's move from Software Engineer II / AI Engineer at Microsoft Dublin into senior, lead, or architect-level customer-facing AI delivery roles. The dashboard combines current roles from official public career feeds with a practical UAE sponsorship strategy.

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
- **Role family:** hands-on engineering plus architecture plus enterprise customers: Forward Deployed, Applied AI/Value, Customer/Field, Solutions/Delivery Architect, Deployment, and Technical Consultant roles.
- **Open status:** a role must be present in a live official ATS/career feed. HTTP 200 alone is not enough; Workday detail records must remain applyable.
- **Compensation:** only explicit AED or EUR ranges from the official posting are shown. Missing pay stays “Not posted”; there are no estimates.
- **Sponsorship:** listing evidence is classified as explicit sponsorship, relocation support, normal employer-sponsored UAE permit pathway, unknown, or explicit no-sponsorship. The normal UAE pathway is not represented as a promise by a particular employer.
- **Failures:** adapters are isolated. A failed source preserves its prior records as stale/source-error records and excludes them from the live count.

## Official automated sources

- Greenhouse public job-board API: Databricks, Anthropic, Celonis
- Ashby public posting feed: OpenAI
- Lever public posting API: Palantir
- Amazon Jobs official JSON search: AWS
- Workday public career endpoints plus applyability detail checks: Salesforce, NVIDIA

Microsoft, Google Cloud, Oracle, IBM, ServiceNow, G42/Core42/Presight, Careem, and Accenture were considered, but are not configured where a stable, public, unattended feed could not be verified. The app does not fill gaps with aggregators.

## Dashboard

- Search and filter by company, sponsorship evidence, minimum score, and local pipeline status.
- Inspect the full factor breakdown and official evidence excerpt.
- Keep progress in browser `localStorage`: New, Reviewing, Shortlisted, Applied, Interviewing, Offer, Rejected, Withdrawn, or Archived.
- Review per-source health and the latest generation timestamp.
- Export the filtered view to CSV with both the raw official URL and a spreadsheet-clickable `HYPERLINK` formula. Untrusted text is formula-injection protected.
- Read a visible sponsorship strategy covering the employment-visa workflow, target tiers, CV positioning, recruiter questions, red flags, cadence, networking, and offer diligence.

## UAE visa sources

The strategy links to primary public guidance rather than promising eligibility:

- [UAE Government — job offers, work permits and contracts](https://u.ae/en/information-and-services/jobs/employment-in-the-private-sector/job-offers-and-work-permits-and-contracts)
- [UAE Government — preparing to work](https://u.ae/en/information-and-services/jobs/working-in-uae)
- [MOHRE — overseas worker permit service](https://www.mohre.gov.ae/en/services/work-permit-for-recruiting-a-worker-from-outside-the-state-2022)

Re-check the linked government guidance before relying on it; immigration procedures can change.

## Automation

- `ci.yml`: tests and compile check.
- `refresh.yml`: daily official-source refresh and generated-data commit.
- `pages.yml`: explicit GitHub Pages deployment.

All workflows use GitHub's built-in permissions and current requested action majors. They reference no repository secrets.

## License

MIT — see [LICENSE](LICENSE).
