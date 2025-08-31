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


