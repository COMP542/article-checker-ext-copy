// ============================================================
// FILE: extension/popup.js
// PURPOSE:
//   Controls the popup UI:
//   - request article extraction
//   - send data to backend
//   - display JSON result
//
// CTRL+F TAGS:
//   [POPUP_UI]
//   [BACKEND_POST]
//   [BACKEND_FALLBACK_URLS]
//   [DISPLAY_SCORE]
//   [ANALYZE_BUTTON_FLOW]
// ============================================================

const extractBtn = document.getElementById("extractBtn");
const statusEl = document.getElementById("status");
const infoEl = document.getElementById("info");

const tabArticle = document.getElementById("tabArticle");
const tabAnalysis = document.getElementById("tabAnalysis");

const panelArticle = document.getElementById("panelArticle");
const panelAnalysis = document.getElementById("panelAnalysis");

const previewArticle = document.getElementById("previewArticle");
const previewAnalysis = document.getElementById("previewAnalysis");

function setStatus(message, isError = false) {
  // [POPUP_STATUS]
  // Updates the small status text shown in the popup.
  statusEl.textContent = message || "";
  statusEl.className = isError ? "meta error" : "meta";
}

function showTab(name) {
  // [POPUP_UI]
  // Switch between the raw article preview tab and analysis results tab.
  const showArticle = name === "article";

  tabArticle.classList.toggle("active", showArticle);
  tabAnalysis.classList.toggle("active", !showArticle);

  panelArticle.classList.toggle("active", showArticle);
  panelAnalysis.classList.toggle("active", !showArticle);
}

tabArticle.addEventListener("click", () => showTab("article"));
tabAnalysis.addEventListener("click", () => showTab("analysis"));

async function getActiveTab() {
  // Find the currently focused browser tab.
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function extractFromPage(tabId) {
  // Ask content.js to extract article data from the current page.
  const response = await browser.tabs.sendMessage(tabId, { type: "EXTRACT_ARTICLE" });

  if (!response?.ok) {
    throw new Error(response?.error || "Failed to extract article text.");
  }

  return response.data;
}

async function postToBackend(payload) {
  // [BACKEND_POST] [BACKEND_FALLBACK_URLS]
  // Try remote backend first, then localhost as fallback.
  const urls = [
    "http://104.248.67.141:5000/analyze",
    "http://127.0.0.1:5000/analyze",
  ];

  let lastError;

  for (const url of urls) {
    try {
      console.log(`Trying backend: ${url}`);

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json?.error?.message || `HTTP ${res.status}`);
      }

      console.log(`Success with backend: ${url}`, json);
      return json;

    } catch (err) {
      lastError = err;
      console.error(`Error with backend ${url}:`, err);
      continue;
    }
  }

  throw new Error(`All backends failed. Last error: ${lastError?.message}`);
}

extractBtn.addEventListener("click", async () => {
  // [ANALYZE_BUTTON_FLOW]
  // Main popup workflow after user clicks the button.
  try {
    setStatus("Capturing article...");
    infoEl.textContent = "";
    previewArticle.textContent = "";
    previewAnalysis.textContent = "";

    const tab = await getActiveTab();
    const extracted = await extractFromPage(tab.id);

    const { title, url, text, wordCount } = extracted;

    // Show the extracted raw article data in the Article tab.
    previewArticle.textContent =
      `TITLE:\n${title}\n\nURL:\n${url}\n\nWORDS:\n${wordCount}\n\nTEXT:\n${text}`;

    setStatus("Sending to backend...");

    // Send article data to Flask API.
    const analysis = await postToBackend({ title, url, text });

    // Show full JSON response for debugging / inspection.
    previewAnalysis.textContent = JSON.stringify(analysis, null, 2);

    // [DISPLAY_SCORE]
    // This is where the popup displays the final percentage score and label.
    infoEl.textContent =
      `Consistency score: ${analysis.score}% | Words: ${analysis.input?.wordCount ?? wordCount}\nLabel: ${analysis.label}`;

    setStatus("Analysis complete. Label and percentage score is not for determining validity, or how true information is.");

    // Automatically switch user to the analysis tab after completion.
    showTab("analysis");
  } catch (err) {
    setStatus("Error occurred", true);
    infoEl.textContent = err.message || String(err);
  }
});