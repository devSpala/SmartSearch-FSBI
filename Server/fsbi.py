# fsbi.py
import os
import json
import random
import math
import hashlib
import numpy as np
from bitarray import bitarray
from typing import List, Dict, Any, Tuple

# Configuration constants
DEFAULT_M = 2048  # bits per Bloom filter node (tuneable)
DEFAULT_K_LEX = 2  # number of lexical hashes
DEFAULT_K_SEM = 2  # number of semantic hash functions (from projection)
DEFAULT_R = 64  # random projection dimension
DIFF_PRIV_FLIP_PROB = 0.01  # optional differential privacy bit flip prob

def murmur_hash32(s: str, seed: int = 0) -> int:
    # Use sha256 as deterministic substitute (fast enough for prototype)
    h = hashlib.sha256((str(seed) + s).encode('utf-8')).hexdigest()
    return int(h[:8], 16)

class SemanticProjector:
    """
    Lightweight semantic projector using random projections
    of character n-gram count vectors. Replaceable with TF-Lite model.
    """
    def __init__(self, r=DEFAULT_R, seed=42):
        random.seed(seed)
        np.random.seed(seed)
        self.r = r
        # Random projection matrix p x r where p = number of n-grams considered.
        # For prototype, we'll compute projection on the fly using char ngrams hashing.
        self._seed = seed

    def project(self, token: str) -> np.ndarray:
        # Build small vector of hashed n-grams positions and project
        # For simplicity we create an r-dim vector by hashing token+nGram seeds
        vec = np.zeros(self.r, dtype=float)
        token = token.lower()
        # use n-grams 1..3
        for n in (1,2,3):
            for i in range(len(token)-n+1):
                ngram = token[i:i+n]
                h = murmur_hash32(ngram, seed=self._seed)  # deterministic int
                idx = h % self.r
                vec[idx] += 1.0
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def semantic_hashes(self, token: str, k: int, m: int) -> List[int]:
        # Convert projected vector into k integer indexes in [0, m-1]
        z = self.project(token)
        # Use random linear projections (signed) to produce bits
        idxs = []
        for j in range(k):
            # create deterministic projection with per-j seed
            rng = np.random.RandomState(hash((j, self._seed)) & 0xffffffff)
            proj = rng.randn(self.r)
            score = float(np.dot(proj, z))
            # map score to index deterministically
            # quantize: map to 0..m-1 by hashing string(token + j + score)
            combined = f"{token}|{j}|{round(score,6)}"
            idx = murmur_hash32(combined, seed=j) % m
            idxs.append(int(idx))
        return idxs

class BloomNode:
    def __init__(self, m_bits=DEFAULT_M, level=0, name=""):
        self.m = m_bits
        self.bits = bitarray(self.m)
        self.bits.setall(0)
        self.level = level
        self.name = name  # for debugging
        self.children = {}  # token->BloomNode or phrase->BloomNode

    def insert_indexes(self, idxs: List[int]):
        for i in idxs:
            self.bits[i % self.m] = 1

    def noisy_bits(self, flip_prob: float = DIFF_PRIV_FLIP_PROB):
        # Return noisy copy (do not mutate original unless intended)
        noisy = self.bits.copy()
        if flip_prob <= 0:
            return noisy
        # flip some bits
        for i in range(self.m):
            if random.random() < flip_prob:
                noisy[i] = not noisy[i]
        return noisy

    def match_score(self, idxs: List[int]) -> float:
        hits = sum(1 for i in idxs if self.bits[i % self.m])
        return hits / len(idxs) if len(idxs) > 0 else 0.0

class FSBIIndex:
    def __init__(self, m_bits=DEFAULT_M, k_lex=DEFAULT_K_LEX, k_sem=DEFAULT_K_SEM):
        self.m = m_bits
        self.k_lex = k_lex
        self.k_sem = k_sem
        self.projector = SemanticProjector(r=DEFAULT_R)
        self.docs = {}  # doc_id -> metadata (title etc.)
        self.trees = {}  # doc_id -> root BloomNode

    # Fractal decomposition: returns list of subsequences by level
    def fractal_decompose(self, text: str, max_phrase_len: int = 3) -> Dict[int, List[str]]:
        # Levels:
        # 1: characters, 2: bigrams, 3: full tokens, 4+: phrase-level up to max_phrase_len
        text = text.strip().lower()
        tokens = [t for t in text.split() if t]
        levels = {}
        # Level 1: characters of the full text
        levels.setdefault(1, [])
        for ch in text:
            if ch.strip():
                levels[1].append(ch)
        # Level 2: bigrams per token
        levels.setdefault(2, [])
        for t in tokens:
            for i in range(len(t)-1):
                levels[2].append(t[i:i+2])
        # Level 3: tokens
        levels.setdefault(3, []).extend(tokens)
        # Level >=4: phrases
        for L in range(2, max_phrase_len+1):
            lvl = 3 + L - 1
            levels.setdefault(lvl, [])
            for i in range(len(tokens)-L+1):
                levels[lvl].append(" ".join(tokens[i:i+L]))
        return levels

    def _lex_hashes(self, s: str, k: int) -> List[int]:
        # simple lexicographic hashes: murmur variations
        return [murmur_hash32(s, seed=j) % self.m for j in range(k)]

    def _sem_hashes(self, s: str, k: int) -> List[int]:
        return self.projector.semantic_hashes(s, k, self.m)

    def index_document(self, doc_id: str, text: str, metadata: Dict[str, Any] = None):
        # create root node for doc
        root = BloomNode(m_bits=self.m, level=0, name=f"{doc_id}_root")
        decomposition = self.fractal_decompose(text)
        # insert all subsequences at appropriate nodes: create child nodes per token/phrase
        for lvl, subseqs in decomposition.items():
            for subseq in subseqs:
                # insert into root as doc-level summary
                lex_idxs = self._lex_hashes(subseq, self.k_lex)
                sem_idxs = self._sem_hashes(subseq, self.k_sem)
                root.insert_indexes(lex_idxs + sem_idxs)
                # per-subsequence child node
                child_name = f"l{lvl}:{subseq}"
                if child_name not in root.children:
                    root.children[child_name] = BloomNode(m_bits=self.m, level=lvl, name=child_name)
                root.children[child_name].insert_indexes(lex_idxs + sem_idxs)
        # Save doc
        self.docs[doc_id] = {"text": text, "meta": metadata or {}}
        self.trees[doc_id] = root

    def query(self, query_text: str, top_k: int = 10, thresholds: Dict[int, float] = None) -> List[Tuple[str, float]]:
        """
        Query FSBI: returns ranked list of (doc_id, score).
        thresholds: level->min_match_score to descend
        """
        thresholds = thresholds or {}
        q_decomp = self.fractal_decompose(query_text)
        candidates = []
        for doc_id, root in self.trees.items():
            # root match
            root_hits = 0
            root_total = 0
            for lvl, subseqs in q_decomp.items():
                for s in subseqs:
                    ids = self._lex_hashes(s, self.k_lex) + self._sem_hashes(s, self.k_sem)
                    root_hits += sum(1 for i in ids if root.bits[i % self.m])
                    root_total += len(ids)
            root_score = (root_hits / root_total) if root_total > 0 else 0.0
            if root_score < thresholds.get(0, 0.01):
                continue  # prune
            # descend: compute weighted score combining matching child nodes
            score = 0.0
            total_w = 0.0
            for lvl, subseqs in q_decomp.items():
                for s in subseqs:
                    child_name = f"l{lvl}:{s}"
                    idxs = self._lex_hashes(s, self.k_lex) + self._sem_hashes(s, self.k_sem)
                    # if child exists, use child match; else use root bits as fallback
                    if child_name in root.children:
                        m = root.children[child_name].match_score(idxs)
                    else:
                        m = root.match_score(idxs)
                    w = 1.0 / (1 + lvl)  # weight inversely with level depth (example)
                    score += w * m
                    total_w += w
            final_score = score / total_w if total_w > 0 else 0.0
            candidates.append((doc_id, float(final_score)))
        # sort and return top_k
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def get_doc(self, doc_id: str) -> Dict[str, Any]:
        return self.docs.get(doc_id, {})

    def export_index_snapshot(self) -> Dict[str, Any]:
        # Export only bitarrays as lists of ints (compressed approach possible)
        out = {}
        for doc_id, root in self.trees.items():
            out_doc = {
                "root_bits": root.bits.to01(),
                "children": {k: v.bits.to01() for k, v in root.children.items()},
                "meta": self.docs[doc_id]["meta"]
            }
            out[doc_id] = out_doc
        return out
