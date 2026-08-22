# Design QA

## Evidence

- Source visual truth:
  `/Users/leowu/.codex/generated_images/01a029f3-d0d8-7812-9f79-a171d7a4bb9e/exec-5e1c7854-af69-4298-86a5-bd4c90a7f419.png`
- Browser implementation: `/Users/leowu/self/raspberry-pi-5-local-rag/implementation-desktop.png`
- Responsive implementation: `/Users/leowu/self/raspberry-pi-5-local-rag/implementation-mobile.png`
- Combined comparison capture: `/Users/leowu/self/raspberry-pi-5-local-rag/qa-comparison.png`
- Source pixels: 1488 × 1058; implementation pixels: 1425 × 1082 browser full-page capture.
- CSS viewport: 1440 × 1024 desktop and 390 × 844 mobile; browser device density was unchanged. Layout widths were
  compared proportionally because the generated source uses a 1488 px canvas.
- State: 對話 selected, populated question, 繁體中文, 標準 retrieval, completed answer, two citations, all three primary
  runtime services healthy.

## Full-view comparison

The implementation preserves the source composition: centered 860 px content column, header above one paper panel,
two-segment navigation, metadata line, textarea, paired selects, full-width fluorescent action, divider-led answer, two
source rows, and centered service footer. The responsive documents state was also captured at 390 × 844 with no
horizontal overflow (`scrollWidth = viewport = 390`).

## Required fidelity surfaces

- Fonts and typography: Inter/system sans stack, bold tightly tracked display heading, 14–16 px UI text, matching
  hierarchy and readable Traditional Chinese fallbacks. No clipping or unintended truncation.
- Spacing and layout rhythm: centered panel, 20 px radius, reference-like header offset, field gaps, dividers, answer
  spacing and footer rhythm. Proportions remain stable after viewport normalization.
- Colors and tokens: matched `#f3f4e9`, `#fffef8`, `#20230f`, `#6d705f`, `#dcdecf`, and `#e9f45b`; no unapproved
  gradients or glows.
- Image and icon fidelity: the target contains no raster product imagery. Phosphor outline icons match the thin
  document, upload, delete, and external-reference marks; no handcrafted SVG/CSS art or placeholder assets are used.
- Copy and content: required title, subtitle, tabs, labels, choices, query, answer, citation filenames/chunks,
  12-document metadata, 3,846 chunks, and service footer match the selected concept's active state.

Focused region comparison was not required: the source and rendered full-resolution captures keep every control, label,
answer line, citation row, and footer readable. The source/result and mobile document-state captures were separately
opened at original resolution.

## Comparison history

- Earlier P2: the first browser capture displayed `2 個文件 · 3,846 個區塊 · 已同步`, while the selected design
  displayed `12 個文件 · 3,846 個區塊 · 剛剛同步`.
- Fix: updated the development-only visual-QA dataset to 12 documents and aligned the synchronization copy. Production
  continues to display actual API counts.
- Post-fix evidence: `implementation-desktop.png` and `qa-comparison.png` show the corrected metadata and no browser
  console warnings or errors.

## Findings

No actionable P0, P1, or P2 visual mismatches remain. The system font rasterization differs slightly from the generative
mock's simulated glyph rendering; this is expected and preferable for accessible code-native Traditional Chinese UI.

## Interactions tested

- Switched between 對話 and 文件 tabs.
- Entered a question, submitted it, received the loading/completed state, answer, and expandable citation rows.
- Loaded document list and responsive upload surface.
- Verified desktop and 390 px mobile layouts with no horizontal overflow.
- Checked browser console warnings/errors: none.

## Follow-up polish

No blocking polish remains. Real Raspberry Pi model latency and native file-picker behavior require on-device acceptance
testing after Ollama and reranker models are installed.

final result: passed
