# Design QA — Five-step local knowledge workflow

## Evidence

- Reference surfaces captured live from `http://127.0.0.1:3001/#upload`, `#configure`, `#edit`, `#visualize`, and `/rag`.
- Implementation captured live from `http://127.0.0.1:3000/` in the same Codex in-app browser session.
- Desktop reference and implementation used the same browser viewport.
- Responsive implementation verified at 390 × 844 CSS pixels with Chrome device-metrics emulation.
- Production state: one legacy processed document, 7 chunks, 56 ArangoDB triples; all data is from the Raspberry Pi stack.

## Comparison

The implementation uses the reference project's workflow concepts—not its dark NVIDIA theme, simulated counts, model
selectors, or storage cards. It preserves the Raspberry Pi app's cream/paper/charcoal/lime design system and implements
five numbered top-level tabs: Upload, Process Documents, Knowledge Triples, Knowledge Graph Visualization, and RAG Search.

Reference-equivalent surfaces are present: drag/drop uploader plus document table and actions; separate Triple Extraction
and Embeddings processing tabs; a searchable triples table with explicit Graph DB storage; the previously verified graph
viewer; and Pure RAG / Graph Search selection above the existing question workflow.

## Findings and fixes

- P1 fixed: upload previously triggered chunking, embeddings, triple extraction, and graph storage as one opaque request.
  New uploads are now persisted first and explicitly processed in later steps.
- P1 fixed: UI controls now map to real backend operations and persistent state; no simulator data is used in production.
- P2 fixed: legacy Qdrant/ArangoDB documents remain visible after the staged-workflow migration.
- P2 fixed: legacy ArangoDB edges are included in the Knowledge Triples table; current production view shows 56 rows.
- P2 fixed: five tabs overflow on narrow screens. Navigation and tables now scroll inside their own containers while the
  document body remains exactly 390 px wide.
- Intentional deviation: model/configuration controls from the DGX app are omitted because this Raspberry Pi stack owns
  its models through environment configuration and should not pretend they can be changed per request.

## Functional verification

- All five primary tabs opened successfully.
- Process Documents switched to Embeddings and rendered real document state.
- Knowledge Triples loaded 56 stored ArangoDB triples.
- Graph Search selection updated and the existing RAG form remained available.
- Test document upload returned `chunk_count: 0`, `embeddings_ready: false`, `triples_ready: false`, proving staged upload.
- The same test document downloaded byte-for-byte and was then removed.
- Desktop browser console errors: none.
- 390 px body overflow: none (`body.scrollWidth = viewport = 390`).
- Frontend `npm run build` and `npm run lint`: passed.
- Backend Python compilation and `git diff --check`: passed. Local pytest package was unavailable; runtime API smoke tests
  and Docker startup covered the changed paths.
- Backend and frontend containers: running.

final result: passed
