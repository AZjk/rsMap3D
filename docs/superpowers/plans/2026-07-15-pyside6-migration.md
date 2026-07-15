# Migrate rsMap3D's GUI from PyQt5 to PySide6 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace PyQt5 with PySide6 as rsMap3D's Qt binding, with zero dialog/layout/behavior changes, migrating bottom-up through the real GUI import graph so each layer's own tests stay verifiable as soon as that layer is done.

**Architecture:** Apply a small, closed set of mechanical text substitutions (see Global Constraints) file by file, in dependency order (Layer 0 → Layer 6), keeping both `PyQt5` and `PySide6` installed until the final task removes `PyQt5`. Two dead files using the removed Qt4 string-signal API are deleted rather than migrated.

**Tech Stack:** PySide6 (replacing PyQt5), Python 3.9+, pytest.

## Global Constraints

- **No dialog layout, workflow, or behavioral changes.** This is a binding swap only.
- **Full cutover, no compatibility shim.** No `qtpy` or hand-rolled abstraction layer.
- Use the `d2607_rsmap3d` conda environment per `CLAUDE.md` for every install/test/verification command in this plan.
- `pyproject.toml` keeps both `PyQt5` and `PySide6` in `dependencies` until the final task (Task 9), which removes `PyQt5`.
- Every task's verification step must include, at minimum, importing each file it touched (`python -c "import rsMap3D.gui.X"`) to catch typos, plus running the tests that exercise that layer and everything below it.

### Migration Rules (apply to every file listed in every task below)

These are the **complete, closed set** of PyQt5 import/API patterns found anywhere in scope (confirmed by exhaustive `grep` across all 28 files touched by this plan — there are no other forms to handle):

| Find (exact line) | Replace with (exact line) |
|---|---|
| `import PyQt5.QtCore as qtCore` | `import PySide6.QtCore as qtCore` |
| `import PyQt5.QtGui as qtGui` | `import PySide6.QtGui as qtGui` |
| `import PyQt5.QtWidgets as qtWidgets` | `import PySide6.QtWidgets as qtWidgets` |
| `import PyQt5.QtTest as qtTest` | `import PySide6.QtTest as qtTest` |
| `from  PyQt5.QtCore import pyqtSignal as Signal` | `from PySide6.QtCore import Signal` |
| `from  PyQt5.QtCore import pyqtSlot as Slot` | `from PySide6.QtCore import Slot` |
| `from PyQt5.QtCore import pyqtSlot` | `from PySide6.QtCore import Slot` |
| `from PyQt5.QtWidgets import QAbstractButton` | `from PySide6.QtWidgets import QAbstractButton` |

Additionally, apply these substitutions to every occurrence found in a file's body (not just the import lines):

| Find | Replace |
|---|---|
| `qtCore.pyqtSlot(` | `qtCore.Slot(` |
| `qtCore.pyqtSignal(` | `qtCore.Signal(` |
| `.exec_()` | `.exec()` |

Do not touch anything else — no reformatting, no reordering imports, no renaming variables. Confirmed clean (do not add handling for these — they don't occur anywhere in scope): `QDesktopWidget`, `QMatrix`, `QStringList`, `AA_*` high-DPI attributes, `QApplication.desktop()`, `.ui` Designer files, `sip`, `QVariant`. Unscoped Qt enum access (`qtCore.Qt.Checked`, `qtCore.Qt.LeftButton`, etc.) needs no change — confirmed working identically in PySide6 6.11.1 (unlike PyQt6, PySide6 does not require fully-scoped enum access).

**Discovered during Task 5 (added here after the fact — this rule was missing from the original closed set and reaches back into already-approved files):** PyQt5's `[type]`-indexed signal-overload syntax (`someSignal[str]`, `someSignal[int]`) is used throughout the codebase, both on custom `Signal(str, name=...)`/`Signal(int, name=...)`-declared signals and on built-in Qt widget signals. Empirically verified against PySide6 6.11.1:
- Custom single-overload signals (e.g. `processError[str]`, `setFileName[str]`, `updateProgress[int]`, `updateParInfo[int]`) — `[type]` indexing **works unchanged**, no fix needed.
- `QCheckBox.stateChanged[int]`, `QSpinBox.valueChanged[int]`, `QComboBox.currentIndexChanged[int]` — **work unchanged**, no fix needed.
- **`QComboBox.currentIndexChanged[str]` fails** with `IndexError: Signature "currentIndexChanged(QString)" not found for signal: "currentIndexChanged". Available candidates: "currentIndexChanged(int)"` — Qt6 removed the `(str)` overload of this signal entirely. The fix is to use the dedicated `currentTextChanged` signal instead (Qt's own replacement for this exact use case; behaviorally identical for the non-editable `QComboBox`es this codebase uses, since a non-editable combo box's displayed text can only change via an index change).

The replacement pattern for every occurrence is the same: change `.currentIndexChanged[str]` to `.currentTextChanged` on that line, keeping whatever `.connect(...)`/`.disconnect(...)`/`.emit(...)` call follows it unchanged. Complete list of the 8 occurrences across the codebase, and which task owns fixing each:
- `src/rsMap3D/gui/input/usescommonoutputtype.py:45` — **Layer 1, already committed in Task 3** — fixed via a follow-up correction (see "Task 3 correction" below), not by editing Task 3's original commit.
- `src/rsMap3D/gui/output/processvtioutputform.py:157` — **Layer 1, already committed in Task 3** — same follow-up correction.
- `src/rsMap3D/gui/input/s1highenergydiffractionform.py:236` — **Layer 3, Task 5's own file set** — fix as part of completing Task 5 correctly.
- `src/rsMap3D/gui/input/s34hdfescanfileform.py:121` — **Layer 3, Task 5's own file set** — fix as part of completing Task 5 correctly.
- `src/rsMap3D/gui/input/fileinputcontroller.py:99,107` (2 occurrences) — **Layer 4, Task 6** — add to that task's Migration Rules application.
- `src/rsMap3D/gui/output/processscanscontroller.py:77,87` (2 occurrences) — **Layer 4, Task 6** — add to that task's Migration Rules application.

#### Task 3 correction (retroactive fix for already-approved files)

Task 3 (Layer 1) is already committed and reviewed, but 2 of its files have the `currentIndexChanged[str]` bug discovered above. Fix as a new, separate commit (do not amend Task 3's original commit — that commit should keep reflecting what was actually reviewed then):

- [ ] In `src/rsMap3D/gui/input/usescommonoutputtype.py:45`, replace:
  ```python
          self.outTypeChooser.currentIndexChanged[str].connect(self._outputTypeChanged)
  ```
  with:
  ```python
          self.outTypeChooser.currentTextChanged.connect(self._outputTypeChanged)
  ```
- [ ] In `src/rsMap3D/gui/output/processvtioutputform.py:157-158` (a multi-line statement), replace:
  ```python
          self.outputTypeSelect.currentIndexChanged[str]. \
              connect(self._selectedTypeChanged)
  ```
  with:
  ```python
          self.outputTypeSelect.currentTextChanged. \
              connect(self._selectedTypeChanged)
  ```
- [ ] Verify both files still import cleanly, re-run `QT_QPA_PLATFORM=offscreen pytest tests/gui/output/test_abstractgridoutputview.py -v` (Layer 1's test) and confirm it still passes.
- [ ] Commit: `git commit -m "Fix currentIndexChanged[str] -> currentTextChanged in Layer 1 files (usescommonoutputtype.py, processvtioutputform.py): Qt6 removed the (str) overload"`

---

### Task 1: Add PySide6 dependency; delete dead Qt4-era code

**Files:**
- Modify: `pyproject.toml`
- Delete: `src/rsMap3D/gui/processscans.py`, `src/rsMap3D/gui/qtsignalstrings.py`
- Modify: `src/rsMap3D/gui/output/processxpcsgridlocationform.py` (remove one dead import line only — this file's PyQt5→PySide6 migration happens later, in Task 5)

**Interfaces:** None — this task only adds a dependency and removes code nothing else calls.

- [ ] **Step 1: Add PySide6 to `pyproject.toml`**

In the `dependencies` list, add `"PySide6",` alongside the existing `"PyQt5",`:

```toml
dependencies = [
    "PyQt5",
    "PySide6",
    "vtk",
    "numpy",
    "xrayutilities",
    "h5py",
    "hdf5plugin",
    "matplotlib",
    "spec2nexus",
    "pillow",
]
```

- [ ] **Step 2: Install and verify**

```bash
pip install -e .
python -c "import PySide6; print(PySide6.__version__)"
```

Expected: prints a version string (e.g. `6.11.1`), no errors.

- [ ] **Step 3: Verify `gui/processscans.py` is truly unreferenced**

```bash
grep -rn "gui\.processscans\|gui import processscans\|ProcessScans\b" src/ tests/ scripts/
```

Expected: no output (confirms nothing imports the `ProcessScans` class before deleting the file).

- [ ] **Step 4: Delete the two dead files**

```bash
git rm src/rsMap3D/gui/processscans.py src/rsMap3D/gui/qtsignalstrings.py
```

- [ ] **Step 5: Remove the dead `qtsignalstrings` import from `processxpcsgridlocationform.py`**

In `src/rsMap3D/gui/output/processxpcsgridlocationform.py`, delete this line (it's unused — the file's real signal wiring already uses new-style `.editingFinished.connect(...)` / `.clicked.connect(...)`, confirmed by grep):

```python
from rsMap3D.gui.qtsignalstrings import EDIT_FINISHED_SIGNAL, CLICKED_SIGNAL
```

- [ ] **Step 6: Verify the remaining codebase still imports cleanly**

```bash
python -c "import rsMap3D.gui.output.processxpcsgridlocationform"
grep -rn "qtsignalstrings" src/ tests/ scripts/
```

Expected: the import succeeds; the grep finds no remaining references anywhere.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "Add PySide6 dependency; delete dead Qt4-era signal code (processscans.py, qtsignalstrings.py)"
```

---

### Task 2: Migrate Layer 0 — base view classes

**Files:**
- Modify: `src/rsMap3D/gui/input/abstractfileview.py`
- Modify: `src/rsMap3D/gui/output/abstractoutputview.py`
- Modify: `tests/gui/output/test_abstractoutputview.py`

**Interfaces:** None — these are base classes with no dependency on any other GUI module (only on the pure-Python string-constant modules `rsm3dcommonstrings.py`/`rsmap3dsignals.py`, which contain no Qt imports and need no changes).

- [ ] **Step 1: Apply the Migration Rules** to `src/rsMap3D/gui/input/abstractfileview.py`, `src/rsMap3D/gui/output/abstractoutputview.py`, and `tests/gui/output/test_abstractoutputview.py`.

- [ ] **Step 2: Verify imports**

```bash
python -c "import rsMap3D.gui.input.abstractfileview"
python -c "import rsMap3D.gui.output.abstractoutputview"
```

Expected: both succeed with no errors.

- [ ] **Step 3: Run the Layer 0 test**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/gui/output/test_abstractoutputview.py -v
```

Expected: all tests pass (same pass/fail state as before this task — this test doesn't touch PyQt5-specific behavior beyond widget construction).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "Migrate Layer 0 to PySide6: abstractfileview.py, abstractoutputview.py"
```

---

### Task 3: Migrate Layer 1

**Files:**
- Modify: `src/rsMap3D/gui/input/usesxmlinstconfig.py`
- Modify: `src/rsMap3D/gui/input/usesxmldetectorconfig.py`
- Modify: `src/rsMap3D/gui/input/usescommonoutputtype.py`
- Modify: `src/rsMap3D/gui/input/abstractimageperfileview.py`
- Modify: `src/rsMap3D/gui/output/abstractgridoutputform.py`
- Modify: `src/rsMap3D/gui/output/processvtioutputform.py`
- Modify: `src/rsMap3D/gui/output/processpowderscanform.py`
- Modify: `tests/gui/output/test_abstractgridoutputview.py`

**Interfaces:** Consumes Layer 0 (`abstractfileview.AbstractFileView`, `abstractoutputview.AbstractOutputView`), already migrated in Task 2.

- [ ] **Step 1: Apply the Migration Rules** to all 8 files listed above.

Additionally, in `src/rsMap3D/gui/input/usesxmldetectorconfig.py`, this file has two `QRegExp`/`QRegExpValidator` usages that also need the QRegExp→QRegularExpression rename (in addition to the standard Migration Rules) — replace:
```python
        rxROI = qtCore.QRegExp(self.DET_ROI_REGEXP_1)
        self.detROITxt.setValidator(qtGui.QRegExpValidator(rxROI,self.detROITxt))
```
with:
```python
        rxROI = qtCore.QRegularExpression(self.DET_ROI_REGEXP_1)
        self.detROITxt.setValidator(qtGui.QRegularExpressionValidator(rxROI,self.detROITxt))
```
and replace:
```python
        rxAvg = qtCore.QRegExp(self.PIX_AVG_REGEXP_1)
        self.pixAvgTxt.setValidator(qtGui.QRegExpValidator(rxAvg,self.pixAvgTxt))
```
with:
```python
        rxAvg = qtCore.QRegularExpression(self.PIX_AVG_REGEXP_1)
        self.pixAvgTxt.setValidator(qtGui.QRegularExpressionValidator(rxAvg,self.pixAvgTxt))
```
and replace:
```python
        rxROI = qtCore.QRegExp(self.DET_ROI_REGEXP_2)
        validator = qtGui.QRegExpValidator(rxROI, None)
```
with:
```python
        rxROI = qtCore.QRegularExpression(self.DET_ROI_REGEXP_2)
        validator = qtGui.QRegularExpressionValidator(rxROI, None)
```
(The regex patterns themselves — `DET_ROI_REGEXP_1`, `DET_ROI_REGEXP_2`, `PIX_AVG_REGEXP_1`, `PIX_AVG_REGEXP_2` — are plain `\d`/`+`/`*`/`,` patterns with no `QRegExp`-specific syntax; `QRegularExpression` supports them unchanged. Do not modify the regex pattern strings themselves.)

- [ ] **Step 2: Verify imports**

```bash
python -c "import rsMap3D.gui.input.usesxmlinstconfig"
python -c "import rsMap3D.gui.input.usesxmldetectorconfig"
python -c "import rsMap3D.gui.input.usescommonoutputtype"
python -c "import rsMap3D.gui.input.abstractimageperfileview"
python -c "import rsMap3D.gui.output.abstractgridoutputform"
python -c "import rsMap3D.gui.output.processvtioutputform"
python -c "import rsMap3D.gui.output.processpowderscanform"
```

Expected: all succeed with no errors.

- [ ] **Step 3: Run the Layer 1 test**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/gui/output/test_abstractgridoutputview.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Manually sanity-check the QRegExp→QRegularExpression conversion**

```bash
python -c "
from PySide6.QtCore import QRegularExpression
for pattern, examples in [
    (r'^(\d*,*)+\$', ['1,1', '1', '', '1,2,3']),
    (r'^(\d)+,(\d)+,(\d)+,(\d)+\$', ['1,487,1,195']),
]:
    rx = QRegularExpression(pattern)
    for ex in examples:
        m = rx.match(ex)
        print(pattern, repr(ex), '-> hasMatch:', m.hasMatch())
"
```

Expected: the ROI-style example (`'1,487,1,195'`) and pixel-averaging-style examples (`'1,1'`, `'1'`, `''`, `'1,2,3'`) all report `hasMatch: True`, confirming `QRegularExpression` accepts the same inputs the original `QRegExp` patterns were designed for.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Migrate Layer 1 to PySide6: usesxmlinstconfig, usesxmldetectorconfig (incl. QRegExp->QRegularExpression), usescommonoutputtype, abstractimageperfileview, abstractgridoutputform, processvtioutputform, processpowderscanform"
```

---

### Task 4: Migrate Layer 2

**Files:**
- Modify: `src/rsMap3D/gui/output/processimagestackform.py`
- Modify: `src/rsMap3D/gui/output/processxpcsgridlocationform.py`
- Modify: `src/rsMap3D/gui/input/specxmldrivenfileform.py`

**Interfaces:** Consumes Layer 1 (`abstractgridoutputform.AbstractGridOutputForm`, `abstractimageperfileview`, `usesxmlinstconfig`, `usesxmldetectorconfig`), already migrated in Task 3.

- [ ] **Step 1: Apply the Migration Rules** to all 3 files.

Additionally, in `src/rsMap3D/gui/input/specxmldrivenfileform.py`, replace:
```python
        rx = qtCore.QRegExp(self.SCAN_LIST_REGEXP)
        self.scanNumsTxt.setValidator(qtGui.QRegExpValidator(rx,self.scanNumsTxt))
```
with:
```python
        rx = qtCore.QRegularExpression(self.SCAN_LIST_REGEXP)
        self.scanNumsTxt.setValidator(qtGui.QRegularExpressionValidator(rx,self.scanNumsTxt))
```
(`SCAN_LIST_REGEXP = r"((\d)+(-(\d)+)?\,( )?)+"` — plain PCRE-compatible pattern, unchanged.)

- [ ] **Step 2: Verify imports**

```bash
python -c "import rsMap3D.gui.output.processimagestackform"
python -c "import rsMap3D.gui.output.processxpcsgridlocationform"
python -c "import rsMap3D.gui.input.specxmldrivenfileform"
```

Expected: all succeed with no errors.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Migrate Layer 2 to PySide6: processimagestackform, processxpcsgridlocationform, specxmldrivenfileform (incl. QRegExp->QRegularExpression)"
```

(No dedicated test exists for these three files in isolation — they're exercised transitively by the Layer 3 test in Task 5.)

---

### Task 5: Migrate Layer 3

**Files:**
- Modify: `src/rsMap3D/gui/input/s33specscanfileform.py`
- Modify: `src/rsMap3D/gui/input/s12specscanfileform.py`
- Modify: `src/rsMap3D/gui/input/s28specscanfileform.py`
- Modify: `src/rsMap3D/gui/input/xpcsspecscanfileform.py`
- Modify: `src/rsMap3D/gui/input/s1highenergydiffractionform.py`
- Modify: `src/rsMap3D/gui/input/s34hdfescanfileform.py`
- Modify: `tests/gui/input/test_s33specscanfileform.py`

**Interfaces:** Consumes Layer 2 (`specxmldrivenfileform`, `processimagestackform`, `processpowderscanform`, `processvtioutputform`, `processxpcsgridlocationform`), already migrated.

- [ ] **Step 1: Apply the Migration Rules** to all 7 files.

Additionally, in `src/rsMap3D/gui/input/s33specscanfileform.py`, `src/rsMap3D/gui/input/s12specscanfileform.py`, and `src/rsMap3D/gui/input/s28specscanfileform.py` (all three have the identical pair of occurrences), replace:
```python
        rxAvg = qtCore.QRegExp(self.PIX_AVG_REGEXP_1)
        self.pixAvgTxt.setValidator(qtGui.QRegExpValidator(rxAvg,self.pixAvgTxt))
```
with:
```python
        rxAvg = qtCore.QRegularExpression(self.PIX_AVG_REGEXP_1)
        self.pixAvgTxt.setValidator(qtGui.QRegularExpressionValidator(rxAvg,self.pixAvgTxt))
```
and replace:
```python
        rxPixAvg = qtCore.QRegExp(self.PIX_AVG_REGEXP_2)
        validator = qtGui.QRegExpValidator(rxPixAvg, None)
```
with:
```python
        rxPixAvg = qtCore.QRegularExpression(self.PIX_AVG_REGEXP_2)
        validator = qtGui.QRegularExpressionValidator(rxPixAvg, None)
```
(`PIX_AVG_REGEXP_1 = r"^(\d*,*)+$"`, `PIX_AVG_REGEXP_2 = r"^((\d)+,*){2}$"` in all three files — unchanged.)

- [ ] **Step 2: Verify imports**

```bash
python -c "import rsMap3D.gui.input.s33specscanfileform"
python -c "import rsMap3D.gui.input.s12specscanfileform"
python -c "import rsMap3D.gui.input.s28specscanfileform"
python -c "import rsMap3D.gui.input.xpcsspecscanfileform"
python -c "import rsMap3D.gui.input.s1highenergydiffractionform"
python -c "import rsMap3D.gui.input.s34hdfescanfileform"
```

Expected: all succeed with no errors.

- [ ] **Step 3: Run the Layer 3 test**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/gui/input/test_s33specscanfileform.py -v
```

Expected: passes. This test calls `S33SpecScanFileForm.createInstance(...)`, which transitively constructs instances from every file in Layers 0–3 — this is the first point in the migration where a genuinely deep construction chain is exercised end to end.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "Migrate Layer 3 to PySide6: s33/s12/s28specscanfileform (incl. QRegExp->QRegularExpression), xpcsspecscanfileform, s1highenergydiffractionform, s34hdfescanfileform"
```

---

### Task 6: Migrate Layer 4

**Files:**
- Modify: `src/rsMap3D/gui/input/fileinputcontroller.py`
- Modify: `src/rsMap3D/gui/output/processscanscontroller.py`

**Interfaces:** Consumes Layer 3 (all the `s*specscanfileform`/`xpcsspecscanfileform`/`s1highenergydiffractionform`/`s34hdfescanfileform` classes), already migrated.

- [ ] **Step 1: Apply the Migration Rules** to both files.

Additionally, in `src/rsMap3D/gui/output/processscanscontroller.py`, delete this line entirely (a dead, unused import of a PyQt5-internal module with no PySide6 equivalent — confirmed unused since the file's real `QDialog` base comes from the `qtWidgets` alias, a different name):
```python
from PyQt5.uic.Compiler.qtproxies import QtWidgets
```

Additionally, apply the `currentIndexChanged[str]` → `currentTextChanged` fix (see the Global Constraints note on this — Qt6 removed the `(str)` overload of `QComboBox.currentIndexChanged`) to these 4 occurrences:

In `src/rsMap3D/gui/input/fileinputcontroller.py`, replace:
```python
        self.formSelection.currentIndexChanged[str].\
            connect(self._selectedTypeChanged)
```
with:
```python
        self.formSelection.currentTextChanged.\
            connect(self._selectedTypeChanged)
```
and replace:
```python
        self.formSelection.currentIndexChanged[str].\
            disconnect(self._selectedTypeChanged)
```
with:
```python
        self.formSelection.currentTextChanged.\
            disconnect(self._selectedTypeChanged)
```

In `src/rsMap3D/gui/output/processscanscontroller.py`, replace:
```python
        self.outputFormSelection.currentIndexChanged[str].connect(
            self._selectedTypeChanged)
```
with:
```python
        self.outputFormSelection.currentTextChanged.connect(
            self._selectedTypeChanged)
```
and replace:
```python
        self.outputFormSelection.currentIndexChanged[str].disconnect(
            self._selectedTypeChanged)
```
with:
```python
        self.outputFormSelection.currentTextChanged.disconnect(
            self._selectedTypeChanged)
```

- [ ] **Step 2: Verify imports**

```bash
python -c "import rsMap3D.gui.input.fileinputcontroller"
python -c "import rsMap3D.gui.output.processscanscontroller"
```

Expected: both succeed with no errors.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Migrate Layer 4 to PySide6: fileinputcontroller.py, processscanscontroller.py (drop dead uic.Compiler.qtproxies import)"
```

---

### Task 7: Migrate Layer 5

**Files:**
- Modify: `src/rsMap3D/gui/dataextentview.py`
- Modify: `src/rsMap3D/gui/datarange.py`
- Modify: `src/rsMap3D/gui/scanform.py`

**Interfaces:** None of these three depend on any other GUI module (only on the pure-Python `rsm3dcommonstrings.py`/`rsmap3dsignals.py`) — they're only *consumed by* `rsmEdit.py` (Layer 6, Task 8).

- [ ] **Step 1: Apply the Migration Rules** to all 3 files. `dataextentview.py` has one `.exec_()` occurrence inside its `if __name__ == "__main__":` self-test block (`sys.exit(app.exec_())`) — this is covered by the standard `.exec_()` → `.exec()` rule.

- [ ] **Step 2: Verify imports**

```bash
python -c "import rsMap3D.gui.dataextentview"
python -c "import rsMap3D.gui.datarange"
python -c "import rsMap3D.gui.scanform"
```

Expected: all succeed with no errors. (`dataextentview.py` exercises the VTK+Qt integration at import time via `from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor` — already empirically confirmed to work with PySide6 during design, but this is the first time it's checked against this specific codebase's import.)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Migrate Layer 5 to PySide6: dataextentview.py, datarange.py, scanform.py"
```

---

### Task 8: Migrate Layer 6 — rsmEdit.py

**Files:**
- Modify: `src/rsMap3D/rsmEdit.py`

**Interfaces:** Consumes every other migrated module (`dataextentview`, `datarange`, `fileinputcontroller`, `processscanscontroller`, `scanform`) — this is the composition root (`MainDialog`). `src/rsMap3D/cli.py` needs no changes: it only does `from rsMap3D.rsmEdit import main as gui_main` inside its `gui`-dispatch branch, a lazy import with no direct Qt exposure.

- [ ] **Step 1: Apply the Migration Rules.** `rsmEdit.py` has one real (non-test-block) `.exec_()` at the bottom of `main()`: `app.exec_()` → `app.exec()`.

- [ ] **Step 2: Verify import**

```bash
python -c "import rsMap3D.rsmEdit"
```

Expected: succeeds with no errors. This is the first point where the entire GUI module tree loads together.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Migrate Layer 6 to PySide6: rsmEdit.py (composition root)"
```

---

### Task 9: Final cutover — remove PyQt5, full verification

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Confirm nothing still references PyQt5**

```bash
grep -rln "PyQt5" src/ tests/ scripts/
```

Expected: no output (or only `src/rsMap3D.egg-info/` generated files, which are gitignored and regenerated — not source).

- [ ] **Step 2: Remove `PyQt5` from `pyproject.toml`**

```toml
dependencies = [
    "PySide6",
    "vtk",
    "numpy",
    "xrayutilities",
    "h5py",
    "hdf5plugin",
    "matplotlib",
    "spec2nexus",
    "pillow",
]
```

- [ ] **Step 3: Fresh install without PyQt5**

```bash
pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip rsMap3D
pip install -e ".[dev,xpcs]"
```

Expected: succeeds; `pip show PyQt5` afterward reports "not found."

- [ ] **Step 4: Run the full test suite**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v
```

Expected: the same 86 passed / 14 pre-existing failures as documented in `.superpowers/sdd/progress.md` (the 14 are unrelated production bugs, not GUI/Qt-binding issues) — no new failures introduced by this migration.

- [ ] **Step 5: Best-effort headless GUI launch**

```bash
QT_QPA_PLATFORM=offscreen timeout 10 rsMap3D || echo "exit code: $?"
```

Expected: the process starts and either runs until the 10-second timeout is hit (exit code 124, meaning it launched and stayed running — a healthy sign for a GUI event loop) or exits cleanly on its own; it must NOT show an `ImportError`, `AttributeError`, or Qt-binding-related traceback. This is a construction smoke test only — it cannot verify visual correctness without a real display.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Remove PyQt5 dependency: PySide6 migration complete"
```

- [ ] **Step 7: Report the required manual follow-up**

This plan cannot perform a real visual verification (this environment has no display). Before considering the migration fully verified, manually launch `rsMap3D` on a machine with a real display and click through the File → Data Range → Scans → Process Data tabs, confirming: file loading, the 3D data-extent view (VTK render window) draws correctly, and the process/output forms' input validators (the `QRegularExpression`-validated pixel-averaging and ROI text fields) still accept/reject the same inputs as before.
