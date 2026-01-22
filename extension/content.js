

function normalizeText(s) {
    return (s||"")
        .replace(/\s+/g, " ")
        .trim();
}

function wordCount(s) {
    const t = normalizeText(s);
    if(!t) return 0;
    return t.split(" ").length;
}

function cloneAndStrip(root) {
    const clone = root.cloneNode(true);

    const junkSelectors = [
        "nav", "footer", "header", "aside",
        "script", "style", "noscript",
        "[role='navigation']",
        ".nav", ".navbar", ".footer", ".header",
        ".sidebar", ".menu", ".advert", ".ads", ".ad",
        ".cookie", ".cookies", ".banner", ".modal",
        "form", "button"
    ]

    for(const sel of junkSelectors) {
        clone.querySelectorAll(sel).forEach(el => el.remove());
    }

    return clone;
}


function getMainText() {
    const body = document.body;
    if(!body) return "";

    const cleaned = cloneAndStrip(body);

    // best signals first
    const preferred = cleaned.querySelector("article") || cleaned.querySelector("main");
    if(preferred) {
        const text = normalizeText(preferred.innerText);
        if(wordCount(text) >= 150) return text;
    }

    // fallback: to pick container with most text
    const candidates = Array.from(cleaned.querySelectorAll("article, main, section, div"))
        .filter(el => el.innerText && el.innerText.length > 0);

    let bestText = "";
    let bestScore = 0;

    for(const el of candidates) {
        const text = normalizeText(el.innerText);
        const wc = wordCount(text);

        const score = wc;

        if(score > bestScore && wc >= 150 && wc <= 8000) {
            bestScore = score;
            bestText = text;
        }
    }

    if(!bestText) {
        const text = normalizeText(cleaned.innerText);
        return text;
    }

    return bestText;
}

browser.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "EXTRACT_ARTICLE") {
    const title = document.title || "";
    const url = location.href;
    const text = (document.body && document.body.innerText) ? document.body.innerText : "";
    const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

    return Promise.resolve({
      ok: true,
      data: { title, url, text, wordCount }
    });
  }
});