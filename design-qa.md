# Design QA — Knowledge Graph

## Evidence

- Source visual truth: live local reference at `http://127.0.0.1:3001/#visualize`, implemented by
  `/Users/leowu/self/dgx-spark-txt2kg/frontend/components/tabs/VisualizeTab.tsx` and its graph viewer.
- Implementation: live Raspberry Pi frontend at `http://127.0.0.1:5173/`, 圖譜 tab.
- Desktop comparison viewport: 1440 × 1024 CSS pixels at the browser's default density.
- Responsive verification: 390 × 844 CSS pixels through Chrome device-metrics emulation.
- State: reference ArangoDB graph populated (80 nodes / 54 relationships); implementation demo graph populated
  (4 entities / 3 relationships). Counts intentionally reflect each source's actual data.

## Visual comparison

The source and implementation were captured in the same browser session and inspected together. The implementation
matches the reference's core composition: bordered visualization card, icon-led title and description, dense single-row
desktop toolbar, large graph stage, force/tree/radial layout choices, database toggle, graph totals, search, export,
fullscreen and zoom controls. The NVIDIA black/green treatment was intentionally translated to the Raspberry Pi app's
existing cream, paper-white, charcoal and fluorescent lime tokens.

The focused toolbar and graph-stage regions remained legible in both captures. The implementation uses the full graph
tab width (up to 1180 px), while chat and document tabs retain their original 860 px measure.

## Findings and fixes

- P1: no blocking visual or functional mismatch remains.
- P2: the original Raspberry Pi graph was a static circular SVG with no controls. It was replaced with an interactive
  D3 force graph and the reference page's information/control hierarchy.
- P2: narrow screens could not fit the desktop toolbar. Controls now wrap into multiple rows and the graph stage scrolls
  internally; at 390 px, document width equals viewport width (`scrollWidth = 390`).
- Intentional deviation: the lightweight 3D option applies perspective to the SVG instead of importing the reference
  project's heavier WebGL renderer, which is more appropriate for Raspberry Pi 5 resources.

## Interactions tested

- Opened the 圖譜 tab and loaded graph data.
- Switched force → tree layout and verified active-state change.
- Searched for `Raspberry` and verified the matching node highlight state.
- Increased zoom from 100% to 115%.
- Verified desktop and 390 px responsive layouts.
- Browser console errors: none.
- `npm run build`: passed.
- `npm run lint`: passed.

final result: passed
