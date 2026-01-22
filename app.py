
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.post("/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    url = (data.get("url") or "").strip()
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "No text provided"})

    wc = len(text.split())
    score = 50
    explanation = [
        "Backend connected successfully.",
        f"Received {wc} words.",
        "Next step: find related articles + compute consistency."
    ]

    return jsonify({
        "ok": True,
        "input": {"title": title, "url": url, "wordCount": wc},
        "score": score,
        "explanation": explanation
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)