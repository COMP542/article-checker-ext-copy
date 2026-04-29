

// extension/popup.js

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
  statusEl.textContent = message || "";
  statusEl.className = isError ? "meta error" : "meta";
}

function showTab(name) {
  const showArticle = name === "article";

  tabArticle.classList.toggle("active", showArticle);
  tabAnalysis.classList.toggle("active", !showArticle);

  panelArticle.classList.toggle("active", showArticle);
  panelAnalysis.classList.toggle("active", !showArticle);
}

tabArticle.addEventListener("click", () => showTab("article"));
tabAnalysis.addEventListener("click", () => showTab("analysis"));

async function getActiveTab() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function extractFromPage(tabId) {
  const response = await browser.tabs.sendMessage(tabId, { type: "EXTRACT_ARTICLE" });

  if (!response?.ok) {
    throw new Error(response?.error || "Failed to extract article text.");
  }

  return response.data;
}

async function postToBackend(payload) {
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
  try {
    setStatus("Capturing article...");
    infoEl.textContent = "";
    previewArticle.textContent = "";
    previewAnalysis.textContent = "";

    const tab = await getActiveTab();
    const extracted = await extractFromPage(tab.id);

    const { title, url, text, wordCount } = extracted;

    previewArticle.textContent =
      `TITLE:\n${title}\n\nURL:\n${url}\n\nWORDS:\n${wordCount}\n\nTEXT:\n${text}`;

    setStatus("Sending to backend...");

    const analysis = await postToBackend({ title, url, text });

    previewAnalysis.textContent = JSON.stringify(analysis, null, 2);

    infoEl.textContent = `Consistency score: ${analysis.score}% | Words: ${analysis.input?.wordCount ?? wordCount}\nLabel: ${analysis.label}`;
    setStatus("Analysis complete. Label and percentage score is not for determining validity, or how true information is.");

    showTab("analysis");
  } catch (err) {
    setStatus("Error occurred", true);
    infoEl.textContent = err.message || String(err);
  }
});