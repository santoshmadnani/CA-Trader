# UI Review & Visual Invariants Rule

## 1. Visual Baseline Alignment Invariant
- **Rule**: The top of the Watchlist (`#mainSidebar`) and the top of the main content / recommendation card (`#dashDualRecoCard`) MUST align horizontally with a delta of $\le 2\text{px}$.
- **Verification**: Run `python tools/ui_reviewer.py` to evaluate `getBoundingClientRect().top` for both elements.

## 2. Section Separation Invariant (No Endless Scrolling)
- **Rule**: Only ONE `.panel` can be visible at a time (`display: block`). All other panels must be hidden (`display: none !important`).
- **Verification**: `python tools/ui_reviewer.py` asserts that `visiblePanels == 1`.

## 3. Dual-Theme Color Integrity (Zero Black Boxes in Light Mode)
- **Rule**: Under light mode (`data-theme="light"`, `data-theme="ivory"`):
  - Every card, container, and sidebar must use `var(--surface)` or clean white/light grey (`#FFFFFF`, `#F8F9FA`).
  - No dark translucent overlays (`rgba(13, 18, 28, ...)`, `#12161f`) are permitted on light surfaces.
- **Verification**: `python tools/ui_reviewer.py` audits computed background colors under light mode and fails if luminance $< 150$.

## 4. Data Freshness & Zero-Blank Policy
- **Rule**: No user-facing item may display empty dashes (`-`, `₹--`, `undefined`, `NaN`).
- **Verification**: When offline or before live ticks arrive, the terminal must immediately render cached fallback prices so the app feels instant ("fast like flash").
