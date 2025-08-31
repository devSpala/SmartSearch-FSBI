# app.py
from flask import Flask, request, jsonify
from fsbi import FSBIIndex
import os

app = Flask(__name__)
INDEX = FSBIIndex(m_bits=2048, k_lex=2, k_sem=2)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "docs": len(INDEX.docs)})

@app.route("/index", methods=["POST"])
def index_doc():
    payload = request.get_json(force=True)
    doc_id = payload["doc_id"]
    text = payload["text"]
    meta = payload.get("meta", {})
    INDEX.index_document(doc_id, text, metadata=meta)
    return jsonify({"status": "indexed", "doc_id": doc_id})

@app.route("/query", methods=["POST"])
def query():
    payload = request.get_json(force=True)
    q = payload.get("q", "")
    top_k = int(payload.get("top_k", 10))
    results = INDEX.query(q, top_k=top_k)
    # expand results with small metadata snippet
    out = []
    for doc_id, score in results:
        doc = INDEX.get_doc(doc_id)
        snippet = doc.get("text", "")[:200]
        out.append({"doc_id": doc_id, "score": score, "snippet": snippet})
    return jsonify({"results": out})

@app.route("/snapshot", methods=["GET"])
def snapshot():
    snap = INDEX.export_index_snapshot()
    return jsonify({"snapshot": snap})

if __name__ == "__main__":
    # simple host for dev
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
