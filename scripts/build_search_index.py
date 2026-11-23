"""Build BM25 and MedCPT + FAISS indexes from the prepared indexing inputs.

  python scripts/build_search_index.py

Writes data/embeddings/medcpt-bm25-v1-<hash>/ (git-ignored). Needs requirements-search.txt.
The first run downloads MedCPT (about 1.6 GB on disk for all three models, once).
"""
import hashlib
import json
import platform
import shutil
import sys

import retrieval as R


def main():
    corpus = R.only_dir(R.ROOT / "data/retrieval", "indexing-inputs-v1-*")
    import faiss
    import numpy as np
    import torch
    import transformers

    # search.py runs offline, so fetch every model now, not just the article encoder used below
    fetcher = R.Models()
    for role in R.MODELS:
        fetcher.get(role)
    del fetcher

    chunk_files = {s: R.sha256_file(corpus / s / "chunks.jsonl") for s in R.SOURCES}
    config = {
        "corpus": str(corpus.relative_to(R.ROOT)), "chunk_files": chunk_files,
        "models": {k: {"name": n, "revision": r} for k, (n, r) in R.MODELS.items()},
        "embedding_input": "pair (context, index_text); CLS pooling; not normalised; no truncation",
        "similarity": "inner product", "faiss_index": "IndexFlatIP (exact)",
        "bm25": {"text": "bm25_context + newline + index_text", "k1": R.BM25_K1, "b": R.BM25_B,
                 "tokenizer": "casefold alphanumeric, stopwords removed, no stemming"},
        "selection": "index_default only", "query_max_tokens": R.QUERY_MAX_TOKENS,
    }
    run_id = "medcpt-bm25-v1-" + hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:20]
    out = R.ROOT / "data/embeddings" / run_id
    if (out / "manifest.json").exists():
        print(f"already built: {out}")
        return
    if out.exists():
        shutil.rmtree(out)  # unfinished earlier attempt of this same run
    (out / "bm25").mkdir(parents=True)

    models, counts, files = R.Models(), {}, {}
    for source in R.SOURCES:
        chunks = R.load_chunks(corpus, source)
        if len({c["chunk_id"] for c in chunks}) != len(chunks):
            raise ValueError("duplicate chunk ids")
        R.BM25.build([c["bm25_context"] + "\n" + c["index_text"] for c in chunks]).save(out / "bm25" / f"{source}.json")

        # identical inputs are encoded once, but every chunk keeps its own row and provenance
        unique = list(dict.fromkeys((c["context"], c["index_text"]) for c in chunks))
        position = {pair: i for i, pair in enumerate(unique)}
        show = lambda done, total: print(f"\r{source}: encoding {done}/{total} unique texts", end="", file=sys.stderr)
        encoded = models.embed("article", [list(p) for p in unique], R.MAX_TOKENS, progress=show)
        print(file=sys.stderr)
        vectors = encoded[[position[(c["context"], c["index_text"])] for c in chunks]]
        if not np.isfinite(vectors).all():
            raise ValueError("non-finite vectors")

        folder = out / source
        folder.mkdir()
        np.save(folder / "vectors.npy", vectors)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(folder / "index.faiss"))
        keep = ("chunk_id", "kg_node_id", "parent_node_id", "linked_node_ids", "evidence_ids", "embedding_input_sha256")
        with open(folder / "row_mapping.jsonl", "w", encoding="utf-8") as handle:
            for row, chunk in enumerate(chunks):
                handle.write(json.dumps({"vector_row": row, **{k: chunk[k] for k in keep}}) + "\n")
        counts[source] = {"rows": len(chunks), "unique_texts_encoded": len(unique), "dimensions": vectors.shape[1]}

    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        files[str(path.relative_to(out))] = R.sha256_file(path)
    software = {"python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__,
                "faiss": faiss.__version__, "numpy": np.__version__}
    manifest = {**config, "run_id": run_id, "counts": counts, "software": software, "files": files}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(counts))
    print(f"written: {out}")


if __name__ == "__main__":
    main()
