## Latest
- Planner recheck 2026-10-08: newest is codex/add-numpy-to-requirements (2025-06-04), docs-only over main.
- Branch `main` (only remote branch on disk). The repo is at `/home/user/tort-os`, not under samuelpmahan. Last commit 2025-06-04, Samuel Mahan: "Rename context db module and fix style (#7)".

## Purpose
A local runtime for the TORTOISE agent network, per its README: self-hosted agent and context services with a NATS bus, semantic routing, a capability registry, and retrieval engines (ANN, Jaccard, TF-IDF) with a vector catalog. Most of the retrieval engines are still stubs.

## Stack
Python modules under `src/`, NATS messaging (`src/nats_bus.py`), `requirements-dev.txt`, `src/setup.sh`, and one test file under `tests/`.

## Key modules
- `/home/user/tort-os/src/context_chunk_shard_db.py` — `ContextChunkShardDB`: storage and lookup of semantic context chunks. Three `pass` bodies remain.
- `/home/user/tort-os/src/vector_catalog.py` — `VectorCatalog` with `add_vector` and `query`.
- `/home/user/tort-os/src/inference_engines/tfidf.py` — `rank_passages`: body is `pass`.
- `/home/user/tort-os/src/inference_engines/jaccard.py` — `match_graphs`: body is `pass`.
- `/home/user/tort-os/src/inference_engines/ann.py` — `search_vectors`: body is `pass`.
- `/home/user/tort-os/src/nats_bus.py` — message bus.

## Reusable for dsdk
- none. Interface sketches only: C5 — `/home/user/tort-os/src/inference_engines/tfidf.py` — the `rank_passages` signature for passage retrieval, with no implementation.

## Evidence quality
- Low. The retrieval engines are unimplemented, and the single test covers `context_chunk_shard_db.py`. Nothing was run.

## Open questions
- Is the stub state current, or has the work moved to another branch or repo? The last commit is from 2025-06-04.
- Are the TORTOISE design docs (`src/AGENTS.md`, `src/SYSTEM_INSTRUCTIONS.md`) the authoritative spec?
