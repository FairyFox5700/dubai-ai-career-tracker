const STATUS_KEY = "dubai-ai-career-tracker.statuses.v1";
const STATUSES = ["new", "reviewing", "shortlisted", "applied", "interviewing", "offer", "rejected", "withdrawn", "archived"];
let allJobs = [];
let sourceReport = { sources: [] };
let visibleJobs = [];

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const statuses = () => { try { return JSON.parse(localStorage.getItem(STATUS_KEY) || "{}"); } catch { return {}; } };
const saveStatus = (id, value) => { const data = statuses(); data[id] = value; localStorage.setItem(STATUS_KEY, JSON.stringify(data)); };
const currentStatus = (job) => statuses()[job.id] || "new";
const sponsorshipLabel = (value) => ({
  explicit_sponsorship: "Explicit sponsorship", employer_work_permit: "Employer permit pathway",
  relocation_support: "Relocation support", unknown: "Unknown", explicit_no_sponsorship: "No sponsorship"
}[value] || value || "Unknown");

function formatComp(value) {
  if (!value) return "Compensation not posted";
  return `${value.currency} ${Number(value.min).toLocaleString()}–${Number(value.max).toLocaleString()} / ${value.period} · official`;
}

function statusOptions(selected) {
  return STATUSES.map(value => `<option value="${value}" ${value === selected ? "selected" : ""}>${value[0].toUpperCase()+value.slice(1)}</option>`).join("");
}

function renderJobs() {
  const query = $("#search-filter").value.trim().toLowerCase();
  const company = $("#company-filter").value;
  const sponsorship = $("#sponsorship-filter").value;
  const pipeline = $("#status-filter").value;
  const minScore = Number($("#score-filter").value || 0);
  visibleJobs = allJobs.filter(job => {
    const haystack = `${job.company} ${job.title} ${job.location} ${job.description_excerpt}`.toLowerCase();
    return (!query || haystack.includes(query)) && (!company || job.company === company) &&
      (!sponsorship || job.sponsorship_status === sponsorship) && (!pipeline || currentStatus(job) === pipeline) &&
      Number(job.score?.total || 0) >= minScore;
  });
  $("#result-line").textContent = `${visibleJobs.length} of ${allJobs.length} verified role${allJobs.length === 1 ? "" : "s"}`;
  $("#empty-state").hidden = visibleJobs.length > 0;
  $("#job-list").innerHTML = visibleJobs.map(job => {
    const red = job.sponsorship_status === "explicit_no_sponsorship";
    const green = job.sponsorship_status === "explicit_sponsorship" || job.sponsorship_status === "relocation_support";
    const factors = Object.entries((job.score && job.score.breakdown) || {}).map(([name,value]) => `<span class="score-factor">${escapeHtml(name.replaceAll("_"," "))}: <strong>${value}</strong></span>`).join("");
    return `<article class="job-card">
      <div><div class="job-top"><span class="company">${escapeHtml(job.company)}</span><span class="pill ${red ? "warn" : green ? "good" : ""}">${escapeHtml(sponsorshipLabel(job.sponsorship_status))}</span><span class="pill">${escapeHtml(formatComp(job.compensation))}</span></div>
      <h3>${escapeHtml(job.title)}</h3><p class="job-location">${escapeHtml(job.location)} · Official ${escapeHtml(job.source)}</p>
      <p class="job-description">${escapeHtml(job.description_excerpt || "Official source record; open the posting for the full description.")}</p>
      <p class="job-evidence"><strong>Sponsorship evidence:</strong> ${escapeHtml(job.sponsorship_evidence)}</p>
      <div class="job-actions"><a href="${escapeHtml(job.url)}" target="_blank" rel="noopener">Open official posting ↗</a><label><span class="sr-only">Pipeline status</span><select class="status-select" data-job-id="${escapeHtml(job.id)}">${statusOptions(currentStatus(job))}</select></label></div></div>
      <div class="score-box"><strong>${Number(job.score?.total || 0)}</strong><span>FIT / 100</span></div><div class="breakdown" aria-label="Score breakdown">${factors}</div>
    </article>`;
  }).join("");
  document.querySelectorAll(".status-select").forEach(select => select.addEventListener("change", event => { saveStatus(event.target.dataset.jobId, event.target.value); renderJobs(); }));
}

function renderHealth() {
  $("#health-grid").innerHTML = (sourceReport.sources || []).map(source => `<article class="health-card"><strong><span class="dot ${source.status}"></span>${escapeHtml(source.company)}</strong><p>${source.status === "ok" ? `${source.live_jobs} matching live role${source.live_jobs === 1 ? "" : "s"}` : `Source error · ${source.jobs_preserved || 0} stale preserved`}</p><small>${escapeHtml(source.kind)}</small></article>`).join("");
}

function csvSafe(value) {
  const text = String(value ?? "");
  return /^[=+\-@]/.test(text) ? `'${text}` : text;
}
function csvCell(value) { return `"${String(value ?? "").replaceAll('"','""')}"`; }
function validHttpUrl(value) { try { const url = new URL(value); return ["http:","https:"].includes(url.protocol); } catch { return false; } }
function downloadCsv() {
  const headers = ["company","title","location","score","sponsorship_status","pipeline_status","raw_application_url","application_link_clickable"];
  const rows = visibleJobs.map(job => {
    const raw_application_url = job.url || "";
    const application_link_clickable = validHttpUrl(raw_application_url) ? `=HYPERLINK("${raw_application_url.replaceAll('"','""')}","Open official posting")` : "";
    return [csvSafe(job.company),csvSafe(job.title),csvSafe(job.location),job.score?.total || "",csvSafe(job.sponsorship_status),csvSafe(currentStatus(job)),raw_application_url,application_link_clickable].map(csvCell).join(",");
  });
  const blob = new Blob([[headers.join(","), ...rows].join("\n")], {type:"text/csv;charset=utf-8"});
  const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "dubai-ai-career-tracker.csv"; link.click(); URL.revokeObjectURL(link.href);
}

async function init() {
  try {
    const [jobsResponse, reportResponse] = await Promise.all([fetch("data/jobs.json"), fetch("data/refresh-report.json")]);
    if (!jobsResponse.ok || !reportResponse.ok) throw new Error("Generated data unavailable");
    const data = await jobsResponse.json(); sourceReport = await reportResponse.json();
    allJobs = (data.jobs || []).filter(job => job.open_status === "verified_open" && !job.stale);
    const companies = [...new Set(allJobs.map(job => job.company))].sort();
    $("#company-filter").insertAdjacentHTML("beforeend", companies.map(name => `<option>${escapeHtml(name)}</option>`).join(""));
    $("#metric-live").textContent = data.live_job_count ?? allJobs.length;
    $("#metric-companies").textContent = companies.length;
    $("#metric-sources").textContent = (sourceReport.sources_ok || []).length;
    $("#metric-updated").textContent = data.generated_at ? new Date(data.generated_at).toLocaleDateString(undefined,{month:"short",day:"numeric"}) : "—";
    renderJobs(); renderHealth();
  } catch (error) {
    $("#result-line").textContent = `Could not load generated data: ${error.message}`;
    $("#empty-state").hidden = false;
  }
}

["#search-filter","#company-filter","#sponsorship-filter","#status-filter","#score-filter"].forEach(selector => document.addEventListener("input", event => { if (event.target.matches(selector)) renderJobs(); }));
document.addEventListener("DOMContentLoaded", () => { $("#export-csv").addEventListener("click", downloadCsv); init(); });
