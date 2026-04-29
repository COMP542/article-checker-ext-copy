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
  if (!tabs.length) {
    throw new Error("No active tab found.");
  }
  return tabs[0];
}

async function extractFromPage(tabId) {
  try {
    const extractResponse = await browser.tabs.sendMessage(tabId, {
      type: "EXTRACT_ARTICLE"
    });

    if (!extractResponse?.ok) {
      throw new Error(extractResponse?.error || "Failed to extract article text.");
    }

    return extractResponse.data;
  } catch (err) {
    if (String(err).includes("Receiving end does not exist")) {
      throw new Error(
        "Content script is not loaded on this page yet. Refresh the tab and try again."
      );
    }
    throw err;
  }
}

async function postToBackend(payload) {
  const urls = [
    "http://104.248.67.141:5000/analyze",
    "http://127.0.0.1:5000/analyze",
  ];

  let lastError = null;

  for (const url of urls) {
    try {
      const apiResponse = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      let result = null;
      try {
        result = await apiResponse.json();
      } catch {
        result = null;
      }

      if (!apiResponse.ok) {
        throw new Error(result?.error?.message || `HTTP ${apiResponse.status}`);
      }

      return result;
    } catch (err) {
      lastError = err;
    }
  }

  throw new Error(`All backends failed. Last error: ${lastError?.message || "Unknown error"}`);
}

function renderArticlePreview({ title, url, text, wordCount }) {
  previewArticle.textContent =
    `TITLE:\n${title}\n\nURL:\n${url}\n\nWORDS:\n${wordCount}\n\nTEXT:\n${text}`;
}

function renderAnalysis(analysis, fallbackWordCount) {
  previewAnalysis.textContent = JSON.stringify(analysis, null, 2);
  infoEl.textContent =
    `Consistency score: ${analysis.score}% | Words: ${analysis.input?.wordCount ?? fallbackWordCount}\n` +
    `Label: ${analysis.label}`;
}

function validateExtractedArticle({ url, text, wordCount }) {
  if (!text || wordCount < 120) {
    const hostname = (() => {
      try {
        return new URL(url).hostname;
      } catch {
        return "";
      }
    })();

    if (hostname.includes("msn.com")) {
      throw new Error(
        "This MSN page appears to be a preview or wrapper, not the full article text. Open the original publisher article and try again."
      );
    }

    throw new Error(
      "Could not extract enough article text from this page. This site may be showing a preview, syndicated shell, or blocked article body. Try opening the original publisher link."
    );
  }
}

async function runAnalysis() {
  setStatus("Capturing article...");
  infoEl.textContent = "";
  previewArticle.textContent = "";
  previewAnalysis.textContent = "";

  const tab = await getActiveTab();
  const extracted = await extractFromPage(tab.id);

  validateExtractedArticle(extracted);
  renderArticlePreview(extracted);

  setStatus("Sending to backend...");
  const analysis = await postToBackend({
    title: extracted.title,
    url: extracted.url,
    text: extracted.text
  });

  renderAnalysis(analysis, extracted.wordCount);

  setStatus(
    "Analysis complete. Label and percentage score is not for determining validity, or how true information is."
  );
  showTab("analysis");
}

extractBtn.addEventListener("click", async () => {
  try {
    await runAnalysis();
  } catch (err) {
    setStatus("Error occurred", true);
    infoEl.textContent = err?.message || String(err);
  }
});