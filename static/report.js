// Phase 1 placeholder: shows the raw report. T5 replaces this with the visual report
// (see docs/tasks/T5-report-ui.md). Report data is untrusted: textContent only.
window.renderReport = (report) => {
  for (const id of ["start", "interview"]) document.getElementById(id).hidden = true;
  const content = document.getElementById("report-content");
  const fit = report.role_fit;
  const heading = document.createElement("h2");
  heading.textContent = `Fit for ${fit.role_title}: ${fit.fit_percent}% (${fit.band})`;
  const raw = document.createElement("pre");
  raw.className = "card";
  raw.textContent = JSON.stringify(report, null, 2);
  content.replaceChildren(heading, raw);
  document.getElementById("report").hidden = false;
};
