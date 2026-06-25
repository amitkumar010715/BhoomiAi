/* ========== DOM ELEMENTS ========== */
const form = document.querySelector("#query-form");
const fetchButton = document.querySelector("#fetch-button");
const reportButton = document.querySelector("#report-button");
const askButton = document.querySelector("#ask-button");
const statusEl = document.querySelector("#status");
const statusText = document.querySelector("#status-text");
const answerText = document.querySelector("#answer-text");
const factsGrid = document.querySelector("#facts-grid");
const sourcesList = document.querySelector("#sources-list");
const fieldCount = document.querySelector("#field-count");
const sourceCount = document.querySelector("#source-count");
const availableCount = document.querySelector("#available-count");
const unavailableCount = document.querySelector("#unavailable-count");
const coverageText = document.querySelector("#coverage-text");
const mapCoords = document.querySelector("#map-coords");
const latInput = document.querySelector("#lat");
const lngInput = document.querySelector("#lng");
const questionInput = document.querySelector("#question");
const openaiKeyInput = document.querySelector("#openai-key");
const clearOpenaiKeyButton = document.querySelector("#clear-openai-key");
const presets = [...document.querySelectorAll(".preset")];
const copyMcpConfigButton = document.querySelector("#copy-mcp-config");
const mcpConfigCode = document.querySelector("#mcp-config-code");
const reportOutput = document.querySelector("#report-output");
const copyReportButton = document.querySelector("#copy-report-button");

// Modal elements
const helpModal = document.querySelector("#help-modal");
const helpBtn = document.querySelector("#help-btn");
const closeHelpBtn = document.querySelector("#close-help");
const modalOverlay = document.querySelector("#modal-overlay");


const storedOpenaiKey = sessionStorage.getItem("bhoomiai_openai_key");
if (storedOpenaiKey && openaiKeyInput) {
  openaiKeyInput.value = storedOpenaiKey;
}

openaiKeyInput?.addEventListener("input", () => {
  const key = openaiKeyInput.value.trim();
  if (key) sessionStorage.setItem("bhoomiai_openai_key", key);
  else sessionStorage.removeItem("bhoomiai_openai_key");
});

clearOpenaiKeyButton?.addEventListener("click", () => {
  if (openaiKeyInput) openaiKeyInput.value = "";
  sessionStorage.removeItem("bhoomiai_openai_key");
  setStatus("Key cleared", "is-ok");
});
let map;
let marker;

/* ========== CONSTANTS ========== */
const defaultFields = [
  "district",
  "elevation_m",
  "nearest_road_distance_m",
  "nearest_water_distance_m",
  "nearest_water_name",
  "nearest_place_name",
];

const fieldCoverage = {
  district: "All Uttar Pradesh district boundaries",
  elevation_m: "Downloaded DEM tiles only",
  nearest_road_distance_m: "OSM sample coverage only",
  nearest_water_distance_m: "OSM sample coverage only",
  nearest_water_name: "OSM sample coverage only",
  nearest_place_name: "OSM sample coverage only",
};

/* ========== MODAL FUNCTIONS ========== */
function openHelpModal() {
  helpModal.classList.add("is-open");
  helpModal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeHelpModal() {
  helpModal.classList.remove("is-open");
  helpModal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

helpBtn?.addEventListener("click", openHelpModal);
closeHelpBtn?.addEventListener("click", closeHelpModal);
modalOverlay?.addEventListener("click", closeHelpModal);

// Close modal on Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && helpModal?.classList.contains("is-open")) {
    closeHelpModal();
  }
});

/* ========== STATUS FUNCTIONS ========== */
function setStatus(text, className) {
  if (statusEl && statusText) {
    statusText.textContent = text;
    statusEl.className = `status ${className}`;
  }
}

function setBusy(action) {
  setStatus(action + "...", "is-busy");
  askButton.disabled = true;
  fetchButton.disabled = true;
  if (reportButton) reportButton.disabled = true;
}

function setOk(text) {
  askButton.disabled = false;
  fetchButton.disabled = false;
  if (reportButton) reportButton.disabled = false;
  setStatus(text, "is-ok");
}

function showError(error) {
  askButton.disabled = false;
  fetchButton.disabled = false;
  if (reportButton) reportButton.disabled = false;
  setStatus("Error", "is-error");
  answerText.textContent = error.message;
}

/* ========== PRESET BUTTONS ========== */

presets.forEach((button) => {
  button.addEventListener("click", async () => {
    presets.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    if (button.dataset.lat) latInput.value = button.dataset.lat;
    if (button.dataset.lng) lngInput.value = button.dataset.lng;
    questionInput.value = button.dataset.question;
    syncMapFromInputs({ pan: true });
    if (button.dataset.lat && button.dataset.lng) await askQuestion();
  });
});

latInput.addEventListener("input", () => {
  clearPresetSelection();
  syncMapFromInputs({ pan: false });
});
lngInput.addEventListener("input", () => {
  clearPresetSelection();
  syncMapFromInputs({ pan: false });
});

latInput.addEventListener("change", () => syncMapFromInputs({ pan: true }));
lngInput.addEventListener("change", () => syncMapFromInputs({ pan: true }));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncMapFromInputs({ pan: true });
  await askQuestion();
});

fetchButton.addEventListener("click", async () => {
  syncMapFromInputs({ pan: true });
  await fetchFacts();
});

reportButton?.addEventListener("click", async () => {
  syncMapFromInputs({ pan: true });
  await generateReport();
});

function initMap() {
  if (!window.L) {
    const mapEl = document.querySelector("#map");
    if (mapEl) mapEl.textContent = "Map unavailable";
    return;
  }

  const start = getLatLngFromInputs();
  map = L.map("map", {
    zoomControl: true,
    scrollWheelZoom: true,
  }).setView(start, 7);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  marker = L.marker(start, { draggable: true }).addTo(map);
  marker.on("dragend", async () => {
    const point = marker.getLatLng();
    setCoordinate(point.lat, point.lng, { pan: false, query: true });
  });

  map.on("click", async (event) => {
    setCoordinate(event.latlng.lat, event.latlng.lng, { pan: false, query: true });
  });

  syncMapFromInputs({ pan: false });
}

async function setCoordinate(lat, lng, options = {}) {
  latInput.value = Number(lat).toFixed(6);
  lngInput.value = Number(lng).toFixed(6);
  clearPresetSelection();
  syncMapFromInputs({ pan: options.pan ?? false });
  if (options.query) await askQuestion();
}

function syncMapFromInputs(options = {}) {
  const point = getLatLngFromInputs();
  updateMapCoords(point);
  if (!map || !marker || !Number.isFinite(point[0]) || !Number.isFinite(point[1])) return;
  marker.setLatLng(point);
  if (options.pan) map.setView(point, Math.max(map.getZoom(), 8));
}

function getLatLngFromInputs() {
  return [Number(latInput.value), Number(lngInput.value)];
}

function updateMapCoords(point) {
  if (!mapCoords) return;
  const [lat, lng] = point;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    mapCoords.textContent = "Invalid coordinate";
    return;
  }
  mapCoords.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
}

async function askQuestion() {
  setBusy("Asking");
  try {
    const payload = getBasePayload();
    const data = await postJson("/v1/ask", payload);
    const counts = countAvailability(data.results);
    answerText.textContent = enrichAnswer(data.answer, counts);
    renderFacts(data.results);
    renderSources(data.citations, data.results);
    renderCoverage(data.results, data.location);
    if (isReportQuestion(payload.question)) {
      const reportData = await postJson("/v1/report", payload);
      renderReport(reportData);
    } else {
      renderQuickReport({
        location: data.location,
        question: data.question,
        summary: data.answer,
        results: data.results,
        citations: data.citations,
      });
    }
    fieldCount.textContent = `${counts.available}/${counts.total} available`;
    setOk("Ready");
  } catch (error) {
    showError(error);
  }
}

async function fetchFacts() {
  setBusy("Fetching");
  try {
    const payload = { ...getBasePayload(), fields: defaultFields };
    delete payload.question;
    const data = await postJson("/v1/fetch", payload);
    const counts = countAvailability(data.results);
    answerText.textContent = buildFetchSummary(data.location, counts);
    renderFacts(data.results);
    renderSources(data.citations, data.results);
    renderCoverage(data.results, data.location);
    renderQuickReport({
      location: data.location,
      question: "Fetch facts",
      summary: buildFetchSummary(data.location, counts),
      results: data.results,
      citations: data.citations,
    });
    fieldCount.textContent = `${counts.available}/${counts.total} available`;
    setOk("Ready");
  } catch (error) {
    showError(error);
  }
}

async function generateReport() {
  setBusy("Generating report");
  try {
    const payload = getBasePayload();
    const data = await postJson("/v1/report", payload);
    const counts = countAvailability(data.results);
    answerText.textContent = data.summary;
    renderFacts(data.results);
    renderSources(data.citations, data.results);
    renderCoverage(data.results, data.location);
    renderReport(data);
    fieldCount.textContent = `${counts.available}/${counts.total} available`;
    document.querySelector("#report")?.scrollIntoView({ behavior: "smooth", block: "start" });
    setOk("Report ready");
  } catch (error) {
    showError(error);
  }
}

function renderQuickReport(data) {
  if (!reportOutput || !data?.results) return;
  const location = data.location || {};
  const results = Object.entries(data.results || {});
  const counts = countAvailability(data.results);
  const lines = [
    "# BhoomiAI Site Report Preview",
    "",
    "## Location",
    `- Latitude: ${location.lat ?? "Unavailable"}`,
    `- Longitude: ${location.lng ?? "Unavailable"}`,
    `- State: ${location.state ?? "Unavailable"}`,
    `- District: ${location.district || "Unavailable"}`,
    "",
    "## Question",
    data.question || questionInput.value.trim() || "No question provided.",
    "",
    "## Summary",
    data.summary || "No summary available.",
    "",
    "## Facts",
  ];

  for (const [field, result] of results) {
    lines.push(`- ${labelFor(field)}: ${formatValue(result.value, result.unit)} | Source: ${result.source || "Unknown"}`);
  }

  lines.push(
    "",
    "## Data Coverage",
    `- Available fields: ${counts.available}`,
    `- Unavailable fields: ${counts.unavailable}`,
    "",
    "Use the Report button for the full backend-generated report."
  );

  reportOutput.textContent = lines.join("\n");
}

function isReportQuestion(question) {
  const text = String(question || "").toLowerCase();
  return text.includes("report") || text.includes("site summary") || text.includes("site intelligence");
}
function renderReport(data) {
  if (!reportOutput) return;
  reportOutput.textContent = data.report_markdown || "Report unavailable.";
}

copyReportButton?.addEventListener("click", async () => {
  if (!reportOutput) return;
  try {
    await navigator.clipboard.writeText(reportOutput.textContent);
    const original = copyReportButton.innerHTML;
    copyReportButton.innerHTML = '<i class="fas fa-check"></i> Copied';
    setTimeout(() => {
      copyReportButton.innerHTML = original;
    }, 1400);
  } catch (error) {
    setStatus("Copy failed", "is-error");
  }
});
function getBasePayload() {
  return {
    lat: Number(latInput.value),
    lng: Number(lngInput.value),
    question: questionInput.value.trim(),
  };
}

async function postJson(url, payload) {
  const headers = { "Content-Type": "application/json" };
  const apiKey = openaiKeyInput?.value?.trim();
  if (apiKey && (url === "/v1/ask" || url === "/v1/report")) {
    headers["X-OpenAI-API-Key"] = apiKey;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return data;
}

function renderFacts(results) {
  const entries = Object.entries(results || {});
  factsGrid.innerHTML = "";

  if (entries.length === 0) {
    factsGrid.innerHTML = '<p class="empty">No facts returned.</p>';
    return;
  }

  for (const [key, item] of entries) {
    const available = isAvailable(item);
    const value = formatValue(item.value, item.unit);
    const source = item.source || "Unknown source";
    const note = available ? source : unavailableReason(key, item);
    const fact = document.createElement("article");
    fact.className = `fact ${available ? "is-available" : "is-unavailable"}`;
    fact.innerHTML = `
      <div class="fact-key">${escapeHtml(labelFor(key))}</div>
      <div class="fact-value">${escapeHtml(value)}</div>
      <div class="fact-source">${escapeHtml(note)}</div>
    `;
    factsGrid.appendChild(fact);
  }
}

function renderSources(citations, results) {
  sourcesList.innerHTML = "";
  const list = (citations || []).filter((citation) =>
    (citation.fields || []).some((field) => isAvailable(results?.[field]))
  );
  sourceCount.textContent = `${list.length} sources`;

  if (list.length === 0) {
    sourcesList.innerHTML = '<li>No sources for currently available fields.</li>';
    return;
  }

  for (const citation of list) {
    const availableFields = (citation.fields || []).filter((field) => isAvailable(results?.[field]));
    const firstField = availableFields[0];
    const sourceUrl = firstField && results?.[firstField]?.source_url;
    const sourceLabel = escapeHtml(citation.source);
    const fields = escapeHtml(availableFields.map(labelFor).join(", "));
    const li = document.createElement("li");
    li.innerHTML = sourceUrl
      ? `<a href="${escapeAttribute(sourceUrl)}" target="_blank" rel="noreferrer">${sourceLabel}</a><br>${fields}`
      : `<strong>${sourceLabel}</strong><br>${fields}`;
    sourcesList.appendChild(li);
  }
}

function renderCoverage(results, location) {
  const entries = Object.entries(results || {});
  const counts = countAvailability(results);
  const availableLabels = entries
    .filter(([, item]) => isAvailable(item))
    .map(([key]) => labelFor(key));
  const unavailableLabels = entries
    .filter(([, item]) => !isAvailable(item))
    .map(([key]) => labelFor(key));

  availableCount.textContent = counts.available;
  unavailableCount.textContent = counts.unavailable;

  const place = location?.district || "outside district coverage";
  const available = availableLabels.length ? availableLabels.join(", ") : "none";
  const unavailable = unavailableLabels.length ? ` Unavailable now: ${unavailableLabels.join(", ")}.` : "";
  coverageText.textContent = `${place}: ${available}.${unavailable}`;
}

function countAvailability(results) {
  const items = Object.values(results || {});
  const available = items.filter(isAvailable).length;
  return {
    total: items.length,
    available,
    unavailable: items.length - available,
  };
}

function isAvailable(item) {
  return Boolean(item && item.value !== null && item.value !== undefined && item.value !== "");
}

function enrichAnswer(answer, counts) {
  if (counts.unavailable === 0) return answer;
  return `${answer} Available fields: ${counts.available}. Unavailable fields: ${counts.unavailable}.`;
}

function buildFetchSummary(location, counts) {
  const place = location?.district || "Outside current UP district coverage";
  return `${place}: ${counts.available} available facts and ${counts.unavailable} unavailable fields for this coordinate.`;
}

function unavailableReason(key, item) {
  if (key.startsWith("nearest_")) {
    return "Unavailable outside current OSM sample coverage";
  }
  if (key === "elevation_m") {
    return "Unavailable because this DEM tile is not downloaded yet";
  }
  if (key === "district") {
    return "Outside Uttar Pradesh district boundary coverage";
  }
  return fieldCoverage[key] || item?.source || "Unavailable in current local dataset";
}

function formatValue(value, unit) {
  if (value === null || value === undefined || value === "") return "Unavailable";
  return unit ? `${value} ${unit}` : String(value);
}

function labelFor(key) {
  return key.replaceAll("_", " ");
}

function clearPresetSelection() {
  presets.forEach((item) => item.classList.remove("is-active"));
  document.querySelector(".preset-custom")?.classList.add("is-active");
}


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

/* ========== INITIALIZATION ========== */
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  setOk("Ready");
});

// Initial query on page load
window.addEventListener("load", () => {
  askQuestion().catch(() => {
    // Silently fail on initial load
  });
});







