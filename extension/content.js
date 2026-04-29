// ============================================================
// FILE: extension/content.js
// PURPOSE:
//   Runs inside the web page and extracts title + main article text.
//
// CTRL+F TAGS:
//   [TEXT_NORMALIZATION]
//   [WORD_COUNT]
//   [NOISE_REMOVAL]
//   [TITLE_EXTRACTION]
//   [MAIN_TEXT_EXTRACTION]
//   [EXTENSION_MESSAGE_HANDLER]
// ============================================================

function normalizeText(s) {
    // [TEXT_NORMALIZATION]
    // Collapse repeated whitespace into single spaces.
    return (s || "")
        .replace(/\s+/g, " ")
        .trim();
}

function wordCount(s) {
    // [WORD_COUNT]
    // Used for extraction quality checks.
    const t = normalizeText(s);
    if (!t) return 0;
    return t.split(" ").length;
}

function cloneAndStrip(root) {
    // [NOISE_REMOVAL]
    // Clone the DOM so we can safely remove junk without altering the real page.
    const clone = root.cloneNode(true);

    const junkSelectors = [
        "nav", "footer", "header", "aside",
        "script", "style", "noscript",
        "[role='navigation']",
        ".nav", ".navbar", ".footer", ".header",
        ".sidebar", ".menu", ".advert", ".ads", ".ad",
        ".cookie", ".cookies", ".banner", ".modal",
        "form", "button"
    ];

    for (const sel of junkSelectors) {
        clone.querySelectorAll(sel).forEach(el => el.remove());
    }

    return clone;
}

function getMainTitle() {
    // [TITLE_EXTRACTION]
    // Try common headline locations before falling back to document.title.
    const cleaned = cloneAndStrip(document.documentElement);

    const headlineSelectors = [
        "h1",
        "article h1",
        "[class*='headline']",
        "[class*='title']",
        "main h1",
    ];

    for (const sel of headlineSelectors) {
        const el = cleaned.querySelector(sel);
        if (el) {
            const text = normalizeText(el.innerText);
            if (text && text.length > 0 && text.length < 500) {
                return text;
            }
        }
    }

    // Fallback: clean site suffixes from browser tab title.
    const docTitle = document.title || "";
    const cleaned_title = normalizeText(docTitle)
        .split(/\s*[|\-–—]\s*/)[0]
        .trim();

    return cleaned_title;
}

function getMainText() {
    // [MAIN_TEXT_EXTRACTION]
    // Try <article> or <main> first, since those are strong article signals.
    const body = document.body;
    if (!body) return "";

    const cleaned = cloneAndStrip(body);

    const preferred = cleaned.querySelector("article") || cleaned.querySelector("main");
    if (preferred) {
        const text = normalizeText(preferred.innerText);
        if (wordCount(text) >= 150) return text;
    }

    // Fallback: choose the container with the most useful text.
    const candidates = Array.from(cleaned.querySelectorAll("article, main, section, div"))
        .filter(el => el.innerText && el.innerText.length > 0);

    let bestText = "";
    let bestScore = 0;

    for (const el of candidates) {
        const text = normalizeText(el.innerText);
        const wc = wordCount(text);

        // Right now score is just word count.
        // In the future, this could include paragraph density or link ratio.
        const score = wc;

        if (score > bestScore && wc >= 150 && wc <= 8000) {
            bestScore = score;
            bestText = text;
        }
    }

    if (!bestText) {
        return normalizeText(cleaned.innerText);
    }

    return bestText;
}

console.log("[TruthChecker] content script ready", location.href);

browser.runtime.onMessage.addListener((msg) => {
  // [EXTENSION_MESSAGE_HANDLER]
  // Popup sends EXTRACT_ARTICLE, content script responds with page data.
  if (msg?.type === "EXTRACT_ARTICLE") {
    const title = getMainTitle();
    const url = location.href;
    const text = getMainText();
    const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

    return Promise.resolve({
      ok: true,
      data: { title, url, text, wordCount }
    });
  }

  return undefined;
});