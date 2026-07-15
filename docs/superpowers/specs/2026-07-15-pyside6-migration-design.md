# Migrate rsMap3D's GUI from PyQt5 to PySide6

## Context

rsMap3D's GUI (`src/rsMap3D/gui/`, `src/rsMap3D/rsmEdit.py`) is built on PyQt5. PyQt5 is
maintained by Riverbank Computing under a GPL/commercial dual license; PySide6 is the Qt
Company's own official binding, LGPL-licensed, and the actively-developed forward path (PyQt5
itself is EOL — Qt5 is out of long-term support). This migration is a binding swap only: no
dialog layout, workflow, or behavior changes.

## Scope

Investigation found 28 files touching PyQt5 (~5,844 LOC across GUI files): 24 non-test GUI
modules, `rsmEdit.py`, and 3 GUI test files. All usage is one of:

1. Import statements (`import PyQt5.QtCore as qtCore`, etc.) — mechanical rename to `PySide6`.
2. `pyqtSignal` → `Signal`, `pyqtSlot` → `Slot` — mechanical rename, no call-site changes.
3. `.exec_()` → `.exec()` — 2 occurrences (`rsmEdit.py:243`, real app entry point;
   `dataextentview.py:143`, inside an `if __name__ == "__main__":` self-test block).
4. `QRegExp`/`QRegExpValidator` → `QRegularExpression`/`QRegularExpressionValidator` — 5 files
   (`s33specscanfileform.py`, `s12specscanfileform.py`, `s28specscanfileform.py`,
   `specxmldrivenfileform.py`, `usesxmldetectorconfig.py`), every occurrence the same pattern:
   building a validator for a `QLineEdit` from a fixed regex string constant. `QRegExp` was
   removed in Qt6; `QRegularExpression` is a superset syntax, so each of the 5 patterns needs a
   one-time check that it still matches the same inputs, not a rewrite.
5. `qtCore.QThread` subclassing (`fileinputcontroller.py`'s `LoadScanThread`,
   `processscanscontroller.py`'s `ProcessScanThread`) — API-identical in PySide6, import path
   only.

Confirmed clean (no occurrences anywhere in `src/`): `QDesktopWidget`, `QMatrix`, `QStringList`,
explicit high-DPI `AA_*` attributes, `QApplication.desktop()`, `.ui` Designer files (`uic.loadUi`),
`sip`, `QVariant`. None of these Qt6-breaking patterns are present, so there's no long-tail of
one-off API changes beyond the five patterns above.

**VTK integration (the highest a-priori risk item) — empirically verified working.** Installed
PySide6 6.11.1 and the project's actual VTK 9.6.2 into an isolated venv with no PyQt5 present,
and confirmed `vtk.qt.QVTKRenderWindowInteractor` auto-detects PySide6 correctly (`QWidget` /
`QObject` base classes resolve to `PySide6.QtWidgets` / `PySide6.QtCore`) and a full render
pipeline (renderer, actor, mapper, outline source) constructs successfully. `dataextentview.py`'s
VTK+Qt integration is not expected to need any change beyond the mechanical import/signal
translation.

## Decisions

1. **Full cutover, no compatibility shim.** `PyQt5` is removed from `dependencies` in
   `pyproject.toml` once the migration is complete; no `qtpy`-style abstraction layer. This is a
   single-deployment internal tool, not a library other projects import against a specific Qt
   binding, so a shim would add ongoing complexity for no real benefit.
2. **Delete `gui/processscans.py` and `gui/qtsignalstrings.py`.** `processscans.py`'s
   `ProcessScans` class uses the old Qt4-style string `SIGNAL()`/`.emit()`/`.connect()` API,
   which doesn't exist in PyQt5 or PySide6 — it would already raise `AttributeError` if
   instantiated today, and nothing in the codebase imports it (`grep` confirms). It cannot be
   mechanically translated (there's no PySide6 equivalent of the removed string-signal API to
   translate to), and writing new logic for a class nothing uses would be speculative.
   `qtsignalstrings.py` exists only to supply `processscans.py` with old-style signal-name
   strings; its only other consumer (`processxpcsgridlocationform.py`) imports two of its
   constants but never uses them (dead import, real signal wiring already uses new-style
   `.clicked.connect(...)` etc.) — deleting `qtsignalstrings.py` means also removing that one
   dead import line.
3. **`pyproject.toml` keeps both `PyQt5` and `PySide6` listed as dependencies during the
   migration**, since intermediate states (some files migrated, some not) need both bindings
   importable. The final task removes `PyQt5`, leaving only `PySide6`.
4. **Dependency-layered incremental migration**, following the real cross-file import graph
   (mapped below), not directory structure — `gui/input/` forms depend directly on `gui/output/`
   forms, so a directory-based split wouldn't allow incremental test verification the way the
   dependency-order split does.
5. **Verification is per-layer during the migration, whole-suite only at the end.** After each
   layer, run the tests that exercise that layer and everything below it. The full suite
   (`QT_QPA_PLATFORM=offscreen pytest tests/`) is only meaningful as a whole once the top layer
   (`rsmEdit.py`) is done, since `MainDialog` composes every other GUI module. The final task
   also does a best-effort headless launch of `rsMap3D` (confirms construction doesn't crash, not
   a visual check — this sandboxed environment has no real display) and explicitly calls out that
   a manual click-through (File → Data Range → Scans → Process tabs) on a real machine is the
   last verification step this plan cannot perform itself.

## Dependency-ordered migration layers

Computed from the actual `from rsMap3D.gui...` import graph (not file location). Each layer only
depends on modules in the same or an earlier layer.

- **Layer 0** (base view classes, no gui-file dependencies beyond pure string-constant modules
  `rsm3dcommonstrings.py`/`rsmap3dsignals.py`, neither of which imports Qt):
  `gui/input/abstractfileview.py`, `gui/output/abstractoutputview.py`
- **Layer 1** (depends only on Layer 0):
  `gui/input/usesxmlinstconfig.py`, `gui/input/usesxmldetectorconfig.py`,
  `gui/input/usescommonoutputtype.py`, `gui/input/abstractimageperfileview.py`,
  `gui/output/abstractgridoutputform.py`, `gui/output/processvtioutputform.py`,
  `gui/output/processpowderscanform.py`
- **Layer 2** (depends on Layer 1):
  `gui/output/processimagestackform.py`, `gui/output/processxpcsgridlocationform.py` (also drop
  its dead `qtsignalstrings` import here), `gui/input/specxmldrivenfileform.py`
- **Layer 3** (depends on Layer 2 and the output forms below it):
  `gui/input/s33specscanfileform.py`, `gui/input/s12specscanfileform.py`,
  `gui/input/s28specscanfileform.py`, `gui/input/xpcsspecscanfileform.py`,
  `gui/input/s1highenergydiffractionform.py`, `gui/input/s34hdfescanfileform.py`
- **Layer 4** (depends on Layer 3):
  `gui/input/fileinputcontroller.py`, `gui/output/processscanscontroller.py` (also drop its dead
  `from PyQt5.uic.Compiler.qtproxies import QtWidgets` import here — unused, and has no PySide6
  equivalent anyway)
- **Layer 5** (independent of other GUI files, only used by `rsmEdit.py`; can be done anytime
  before the final layer — grouped last for presentation simplicity):
  `gui/dataextentview.py`, `gui/datarange.py`, `gui/scanform.py`
- **Layer 6** (the composition root, depends on everything above):
  `rsmEdit.py`

GUI test files slot in at the layer their target class first becomes available:
`tests/gui/output/test_abstractoutputview.py` (Layer 0), `tests/gui/output/test_abstractgridoutputview.py`
(Layer 1), `tests/gui/input/test_s33specscanfileform.py` (Layer 3). `tests/gui/test_scan_form.py` is an
empty stub (no test methods) and needs only its import line updated.

## Out of scope

- `scripts/paraview/*.py` — run under ParaView's own bundled Python interpreter, no PyQt5/PySide6
  involvement.
- `src/rsMap3D/cli.py` and `src/rsMap3D/workflows/*.py` — no Qt dependency.
- Any dialog layout, workflow, or behavioral change — this is a binding swap only.
- Fixing the 14 pre-existing, unrelated test failures already documented in
  `.superpowers/sdd/progress.md`.
- A full visual/interactive QA pass — the plan's own verification is automated-tests-plus-launch;
  a manual click-through is called out as a follow-up for a real display.

## Risks

- The 5 `QRegExp`→`QRegularExpression` conversions need each pattern re-verified against the
  same set of valid/invalid example inputs (e.g. pixel-averaging "1,1" style strings, ROI
  "1,487,1,195" style strings) — `QRegularExpression` is a superset syntax so this is expected to
  be a non-issue, but it's the one item in this migration that isn't a pure 1:1 rename.
- No real display in this environment for a true interactive QA pass — mitigated by explicitly
  calling out the manual smoke test as a required follow-up rather than silently skipping it.
