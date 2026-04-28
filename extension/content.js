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

function getMainTitle() {
    const cleaned = cloneAndStrip(document.documentElement);
    
    // Look for article headline in common locations
    const headlineSelectors = [
        "h1",                    // Often the main headline
        "article h1",           // Article-specific headline
        "[class*='headline']",  // Classes named headline
        "[class*='title']",     // Classes named title
        "main h1",              // Main section headline
    ];
    
    for(const sel of headlineSelectors) {
        const el = cleaned.querySelector(sel);
        if(el) {
            const text = normalizeText(el.innerText);
            if(text && text.length > 0 && text.length < 500) {
                return text;
            }
        }
    }
    
    // Fallback: use document.title but try to clean it
    // Remove common suffixes like " | Site Name", " - Site Name", etc.
    const docTitle = document.title || "";
    const cleaned_title = normalizeText(docTitle)
        .split(/\s*[|\-–—]\s*/)[0]  // Take the part before common separators
        .trim();
    
    return cleaned_title;
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

console.log("[TruthChecker] content script ready", location.href);

browser.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "EXTRACT_ARTICLE") {
    const title = getMainTitle();  // Use the new function instead of document.title
    const url = location.href;
    // const text = document.body?.innerText || ""; for the article text
    const text = getMainText();
    const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
    console.log(title)
    return Promise.resolve({
      ok: true,
      data: { title, url, text, wordCount }
    });
  }

  return undefined;
});
