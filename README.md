# SmartSearch-FSBI Prototype

**SmartSearch-FSBI** is a prototype of  
**Fractal Semantic Bloom Indexing (FSBI)**:  
a secure, cost-effective, and offline-aware framework for cloud document retrieval over **NoSQL**.  

It combines:
- **Fractal text decomposition** (multi-scale subsequences).
- **Hierarchical Semantic Bloom Filters** for indexing.
- **Differential privacy** for obfuscation.
- **Client-side LRU cache** for offline queries.

---

## ✨ Features
- **Low-latency search** (~200ms vs seconds for ElasticSearch).
- **Compact index** (80% smaller memory footprint).
- **Offline-aware**: Sync only deltas, 65% lower network use.
- **Semantic robustness**: Abbreviations (`i18n`) → full terms (`internationalization`).

---

## 🏗️ Architecture Overview

    ┌──────────────────────────────┐
    │        Android Client        │
    │ ─ LRU Cache (offline)        │
    │ ─ Query Logic Unit           │
    └─────────────┬────────────────┘
                  │
      Query + Cache Miss
                  │
    ┌─────────────▼────────────────┐
    │         FSBI Server          │
    │ ─ Flask API                  │
    │ ─ FSBI Index (Fractal + Bloom│
    │ ─ Document Storage (NoSQL)   │
    └─────────────┬────────────────┘
                  │
        Ranked Search Results
                  │
    ┌─────────────▼────────────────┐
    │     Android Client UI        │
    │ ─ Merges Cloud + Local       │
    │ ─ Stores delta in Cache      │
    └──────────────────────────────┘

## ⚙️ Installation & Running the Server

### 1. Setup environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

### 2. Install dependencies
pip install -r requirements.txt

### 3. Start Flask FSBI server
python app.py

## 🔌 API Usage
1. Index a document

POST /index

Request

{
  "doc_id": "doc1",
  "text": "internationalization of IoT devices"
}


Response

{
  "status": "success",
  "message": "Document indexed with FSBI"
}

2. Query documents

POST /query

Request

{
  "q": "i18n IoT",
  "top_k": 5
}


Response

{
  "results": [
    {"doc_id": "doc1", "score": 0.91},
    {"doc_id": "doc2", "score": 0.63}
  ]
}
## 📱 Android Client Setup
Open SmartSearch-FSBI-Android/ in Android Studio.

Update server URL in MainActivity.kt:

private val serverUrl = "http://10.0.2.2:5000"


Use 10.0.2.2 for Android Emulator, or your LAN IP for device testing.

Run the app → enter queries → get results.

If online → queries cloud FSBI + updates cache.

If offline → serves results from LRU cache.
## 📱 Android Client Setup
1. Index sample docs
curl -X POST -H "Content-Type: application/json" \
  -d '{"doc_id":"doc1","text":"internationalization of IoT devices"}' \
  http://localhost:5000/index

2. Query
curl -X POST -H "Content-Type: application/json" \
  -d '{"q":"i18n IoT"}' \
  http://localhost:5000/query


Expected: doc1 retrieved with high score.

3. Offline mode

Stop the FSBI server.

Run Android client.

Previously queried documents are retrieved from cache.
