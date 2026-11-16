# Frozen SupplementRx POC graph baseline

This release pins the existing graph by its manifest and every exported file hash; it does not duplicate or modify that graph. Run `supplementsrx_env/bin/python scripts/validate_freeze_full_graph.py` to verify and reproduce it.

- All ten topics have source-separated coverage checks; fixed question cases are not a general answering system.
- Product labels, clinical annotations and Reddit discussion retain distinct evidence roles.
- Pending clinical claims and unresolved mappings remain explicit. This freeze is not clinical approval.
- Source collection completeness, clinical correctness and end-to-end precision/recall remain unestablished.
- Future additions create a new graph/release version; do not overwrite this baseline.
- Next choose an evaluation task and baseline before embeddings or GNN training.
