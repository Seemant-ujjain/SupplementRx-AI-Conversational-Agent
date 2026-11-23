"""Shared retrieval code: BM25, MedCPT + FAISS, Reciprocal Rank Fusion, cross-encoder reranking.

One index per source (natmed, dsld, reddit): results are ranked within a source and never fused
across sources, so a label claim or a Reddit post cannot outrank clinical reference text.
"""
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

# torch and faiss each bundle an OpenMP runtime; on macOS loading both aborts without this.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("natmed", "dsld", "reddit")
MODELS = {  # pinned Hugging Face revisions
    "query": ("ncbi/MedCPT-Query-Encoder", "d83a36cc6b8e3a5c5e9d9d6ba156808c1643dcbc"),
    "article": ("ncbi/MedCPT-Article-Encoder", "d05a736da4bb84ee4057b7f7999485be6ed85465"),
    "cross": ("ncbi/MedCPT-Cross-Encoder", "71caf65d4927987813984f54c284405a13fcca49"),
}
QUERY_MAX_TOKENS = 64   # as in the MedCPT model card
MAX_TOKENS = 512
RRF_K = 60
CANDIDATES = 50         # taken from each of BM25 and dense before fusion
RERANK_TOP = 20         # fused results the cross-encoder rescores
BM25_K1, BM25_B = 1.5, 0.75
STOPWORDS = frozenset(
    "a an and are as at be been but by can could did do does for from had has have how i if in into is it its "
    "me my of on or should so that the their them then there these they this to was we were what when which "
    "who why will with would you your".split())


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def only_dir(parent, pattern):
    found = sorted(p for p in parent.glob(pattern) if p.is_dir())
    if len(found) != 1:
        raise SystemExit(f"expected exactly one {parent.relative_to(ROOT)}/{pattern}, found {len(found)}")
    return found[0]


def load_chunks(corpus, source):
    """Chunks recommended for the default index, in file order. This order defines the index rows."""
    with open(corpus / source / "chunks.jsonl", encoding="utf-8") as handle:
        return [c for c in map(json.loads, handle) if c["index_default"]]


# ---------------------------------------------------------------- BM25 (keyword search)

def tokenize(text):
    """Lowercase alphanumeric words, no stemming. Hyphenated words split: omega-3 -> omega 3."""
    return [t for t in re.findall(r"[^\W_]+", text.casefold()) if t not in STOPWORDS]


class BM25:
    def __init__(self, doc_len, postings):
        self.doc_len, self.postings = doc_len, postings
        self.avg = sum(doc_len) / len(doc_len)

    @classmethod
    def build(cls, texts):
        doc_len, postings = [], defaultdict(list)
        for row, text in enumerate(texts):
            counts = Counter(tokenize(text))
            doc_len.append(sum(counts.values()))
            for term, tf in counts.items():
                postings[term].append([row, tf])
        return cls(doc_len, dict(postings))

    def save(self, path):
        path.write_text(json.dumps({"doc_len": self.doc_len, "postings": self.postings},
                                   ensure_ascii=False, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data["doc_len"], data["postings"])

    def search(self, query, k):
        scores, total = defaultdict(float), len(self.doc_len)
        for term in set(tokenize(query)):
            hits = self.postings.get(term, ())
            idf = math.log(1 + (total - len(hits) + 0.5) / (len(hits) + 0.5))
            for row, tf in hits:
                norm = BM25_K1 * (1 - BM25_B + BM25_B * self.doc_len[row] / self.avg)
                scores[row] += idf * tf * (BM25_K1 + 1) / (tf + norm)
        return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:k]


# ---------------------------------------------------------------- MedCPT models

class Models:
    """Loads each MedCPT model the first time it is needed."""

    def __init__(self):
        self._loaded = {}

    def get(self, role):
        if role not in self._loaded:
            import torch
            from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer
            from transformers.utils import logging
            logging.set_verbosity_error()
            name, revision = MODELS[role]
            kind = AutoModelForSequenceClassification if role == "cross" else AutoModel
            device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
            model = kind.from_pretrained(name, revision=revision).to(device).eval()
            self._loaded[role] = AutoTokenizer.from_pretrained(name, revision=revision), model, device
        return self._loaded[role]

    def embed(self, role, inputs, max_length, batch=32, progress=None):
        """CLS-token vectors (MedCPT's pooling), not normalised: MedCPT similarity is the inner product."""
        import numpy as np
        import torch
        tok, model, device = self.get(role)
        order = sorted(range(len(inputs)), key=lambda i: len("".join(inputs[i])))
        out = np.zeros((len(inputs), model.config.hidden_size), dtype="float32")
        for start in range(0, len(order), batch):
            ids = order[start:start + batch]
            enc = tok([inputs[i] for i in ids], padding=True, return_tensors="pt",
                      truncation=role == "query", max_length=max_length if role == "query" else None)
            if enc["input_ids"].shape[1] > max_length:
                raise ValueError("input over the token limit; refusing to truncate evidence")
            with torch.no_grad():
                hidden = model(**enc.to(device)).last_hidden_state[:, 0]
            out[ids] = hidden.float().cpu().numpy()
            if progress:
                progress(min(start + batch, len(order)), len(order))
        return out

    def rerank(self, query, texts):
        import torch
        tok, model, device = self.get("cross")
        # Scoring only: query + passage can pass 512 tokens, so the passage tail may be cut here.
        enc = tok([[query, t] for t in texts], padding=True, truncation="only_second",
                  max_length=MAX_TOKENS, return_tensors="pt").to(device)
        with torch.no_grad():
            return model(**enc).logits.squeeze(-1).float().cpu().tolist()


# ---------------------------------------------------------------- search

class Searcher:
    def __init__(self, run_dir=None):
        self.run = Path(run_dir) if run_dir else only_dir(ROOT / "data/embeddings", "medcpt-bm25-v1-*")
        self.manifest = json.loads((self.run / "manifest.json").read_text())
        corpus = ROOT / self.manifest["corpus"]
        if not corpus.is_dir():
            raise SystemExit(f"corpus {corpus} is missing; run prepare_indexing_inputs.py")
        self.models, self.chunks, self.bm25, self.faiss = Models(), {}, {}, {}
        for source in SOURCES:
            if sha256_file(corpus / source / "chunks.jsonl") != self.manifest["chunk_files"][source]:
                raise SystemExit(f"{source} chunks changed since indexing; rerun build_search_index.py")
            self.chunks[source] = load_chunks(corpus, source)
            self.bm25[source] = BM25.load(self.run / "bm25" / f"{source}.json")
            mapping = [json.loads(line) for line in open(self.run / source / "row_mapping.jsonl", encoding="utf-8")]
            if [m["chunk_id"] for m in mapping] != [c["chunk_id"] for c in self.chunks[source]]:
                raise SystemExit(f"{source} row mapping does not match the corpus; rerun build_search_index.py")

    def _dense(self, source, query_vec, k):
        import faiss
        if source not in self.faiss:
            faiss.omp_set_num_threads(1)
            self.faiss[source] = faiss.read_index(str(self.run / source / "index.faiss"))
        scores, rows = self.faiss[source].search(query_vec, k)
        return [(int(r), float(s)) for r, s in zip(rows[0], scores[0]) if r >= 0]

    def search(self, query, mode="hybrid", sources=SOURCES, k=3, rerank=False):
        """-> {source: [result]}; mode is bm25, dense or hybrid. Ranks in each result start at 1."""
        vec = self.models.embed("query", [query], QUERY_MAX_TOKENS) if mode != "bm25" else None
        out = {}
        for source in sources:
            ranked = {}
            if mode != "dense":
                ranked["bm25"] = self.bm25[source].search(query, CANDIDATES)
            if mode != "bm25":
                ranked["dense"] = self._dense(source, vec, CANDIDATES)
            fused, ranks = defaultdict(float), defaultdict(dict)
            for method, hits in ranked.items():
                for rank, (row, score) in enumerate(hits, 1):
                    fused[row] += 1 / (RRF_K + rank)
                    ranks[row][method] = (rank, round(score, 2))
            results = self._collapse(source, sorted(fused, key=lambda r: (-fused[r], r)), ranks)
            if rerank and results:
                head = results[:RERANK_TOP]
                scores = self.models.rerank(query, [r["chunk"]["context"] + ". " + r["chunk"]["index_text"] for r in head])
                for result, score in zip(head, scores):
                    result["rerank"] = round(score, 2)
                results = sorted(head, key=lambda r: -r["rerank"])
            out[source] = results[:k]
        return out

    def _collapse(self, source, rows, ranks):
        """Show identical text once (labels reuse wording); keep the other chunk ids for provenance."""
        seen, results = {}, []
        for row in rows:
            chunk = self.chunks[source][row]
            key = re.sub(r"\W+", " ", chunk["index_text"]).casefold().strip()
            if key in seen:
                seen[key]["same_text"].append(chunk["chunk_id"])
                continue
            seen[key] = dict(chunk=chunk, ranks=ranks[row], rerank=None, same_text=[])
            results.append(seen[key])
        return results
