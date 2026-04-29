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

function isJunkParagraph(text) {
    const t = normalizeText(text).toLowerCase();
    if (!t) return true;

    const junkPatterns = [
        "continue reading",
        "more for you",
        "advertisement",
        "sign up",
        "newsletter",
        "follow us",
        "all rights reserved"
    ];

    if (t.length < 40) return true;
    if (junkPatterns.some(p => t.includes(p))) return true;

    const letters = (t.match(/[a-z]/g) || []).length;
    if (letters < 20) return true;

    return false;
}

function getMainTitle() {
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
            const text = normalizeText(el.textContent);
            if (text && text.length > 0 && text.length < 500) {
                return text;
            }
        }
    }

    const docTitle = document.title || "";
    return normalizeText(docTitle)
        .split(/\s*[|\-–—]\s*/)[0]
        .trim();
}


function getMainText() {
    const body = document.body;
    if (!body) return "";

    const cleaned = cloneAndStrip(body);

    const paragraphSelectors = [
        "article p",
        "main p",
        "[role='main'] p",
        ".article p",
        ".story p",
        ".content p",
        "p"
    ];

    let paragraphs = [];

    for (const sel of paragraphSelectors) {
        const found = Array.from(cleaned.querySelectorAll(sel))
            .map(el => normalizeText(el.textContent))
            .filter(text => !isJunkParagraph(text));

        if (found.length >= 3) {
            paragraphs = found;
            break;
        }

        if (found.length > paragraphs.length) {
            paragraphs = found;
        }
    }

    const text = normalizeText(paragraphs.join(" "));
    if (wordCount(text) >= 120) return text;

    const candidates = Array.from(cleaned.querySelectorAll("article, main, section, div"));
    let bestText = "";
    let bestScore = 0;

    for (const el of candidates) {
        const ps = Array.from(el.querySelectorAll("p"))
            .map(p => normalizeText(p.textContent))
            .filter(text => !isJunkParagraph(text));

        if (!ps.length) continue;

        const combined = normalizeText(ps.join(" "));
        const wc = wordCount(combined);

        if (wc > bestScore) {
            bestScore = wc;
            bestText = combined;
        }
    }

    return bestText || "";
}

console.log("[Parallax] content script ready", location.href);
console.log("[Parallax] content script ready", location.href);

browser.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "EXTRACT_ARTICLE") {
    const title = getMainTitle();
    const url = location.href;
    const text = getMainText();
    const wc = text.trim() ? text.trim().split(/\s+/).length : 0;

    console.log("[Parallax] extracted", {
      title,
      url,
      wordCount: wc,
      preview: text.slice(0, 300)
    });

    return Promise.resolve({
      ok: true,
      data: { title, url, text, wordCount: wc }
    });
  }

  return undefined;
});
