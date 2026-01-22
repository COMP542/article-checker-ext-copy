document.addEventListener("DOMContentLoaded", () => {
  const extractBtn = document.getElementById("extractBtn");
  const statusEl = document.getElementById("status");
  const infoEl = document.getElementById("info");
  const previewEl = document.getElementById("preview");

  function setStatus(msg, isError = false) {
    statusEl.textContent = msg;
    statusEl.className = isError ? "meta error" : "meta";
  }

  extractBtn.addEventListener("click", async () => {

    setStatus("Extracting…");
    infoEl.textContent = "";
    previewEl.style.display = "none";
    previewEl.textContent = "";

    try {
      // Get the active tab
      const tabs = await browser.tabs.query({ active: true, currentWindow: true });
      const tab = tabs && tabs[0];

      console.log("Active tab:", tab);

      if (!tab || typeof tab.id !== "number") {
        setStatus("No active tab found", true);
        return;
      }

      // Ask content script for article
      const resp = await browser.tabs.sendMessage(tab.id, {
        type: "EXTRACT_ARTICLE"
      });

      if (!resp || !resp.ok) {
        setStatus("Failed to extract article", true);
        console.error(resp);
        return;
      }

      const { title, url, text, wordCount } = resp.data;

      // send article to Flask backend
      const analysis = await postToBackend({ title, url, text });
      console.log("Analysis:", analysis);

      // Update UI with score
      setStatus(`Score: ${analysis.score}%`);
      infoEl.textContent = (analysis.explanation || []).join(" • ");

      // Preview
      const t = text || "";
      previewEl.textContent = t.slice(0, 700) + (t.length > 700 ? "…" : "");
      previewEl.style.display = "block";

    } catch (err) {
      setStatus("Error occurred", true);
      console.error(err);
    }
  });

  async function postToBackend(article) {
    const res = await fetch("http://127.0.0.1:5000/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(article)
    });

    const json = await res.json().catch(() => null);
    if (!res.ok) {
      throw new Error(
        (json && json.error) ? json.error : `HTTP ${res.status}`
      );
    }
    return json;
  }
});