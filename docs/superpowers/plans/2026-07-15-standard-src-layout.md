# Restructure rsMap3D to a standard src-layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert rsMap3D from a flat `setup.py` layout to a standard `src/` + `tests/` + `pyproject.toml` layout, with a real `[project.scripts]` CLI (GUI + three workflow subcommands) replacing the ad hoc `Scripts/` directory, with zero import-path breakage (`rsMap3D` stays the package name).

**Architecture:** Pure repackaging in five stages — (1) scaffold `pyproject.toml`/`src/`, (2) relocate non-package content (resources, docs, examples, scripts) to their correct homes, (3) migrate the test suite to `tests/` on pytest, (4) build a `src/rsMap3D/cli.py` + `src/rsMap3D/workflows/` package that replaces three of the standalone `Scripts/*.py` utilities with tested, parameterized functions, (5) verify end to end. Every git move uses `git mv` so history is preserved.

**Tech Stack:** Python 3.9+, setuptools (PEP 621 `pyproject.toml`), pytest, PyQt5/VTK/xrayutilities (unchanged runtime deps).

## Global Constraints

- Package import path stays `rsMap3D` (e.g. `from rsMap3D.datasource.Sector33SpecDataSource import ...`) — never renamed to `rsmap3d`.
- Build backend is `setuptools` via PEP 621 `[project]` + `[tool.setuptools]` tables. No `setup.py`, no `MANIFEST.in`.
- `requires-python = ">=3.9"` (needed for `importlib.resources.files`).
- Root-level `*.xml` files that live directly under `rsMap3D/resources/` today are package data and move to `src/rsMap3D/resources/`, declared via `[tool.setuptools.package-data]`. Every other file under `rsMap3D/resources/` (all subdirectories, `.rsMap3D`, `badpixels.txt`, `ff_data.tif`) is test-only and moves to `tests/fixtures/`. `resources/powderscan_newRSM3D.py` and `resources/powderscan_win.py` are old reference scripts (not fixtures, not package data) and move to `scripts/`.
- Tests move to `tests/` (outside `src/`), renamed to pytest's `test_*.py` discovery pattern, run with `pytest` (added as a `dev` optional-dependency). Test *code* stays `unittest.TestCase`-based — no rewrites beyond fixing what's broken.
- No behavior changes to any existing mapper, datasource, transform, or GUI class — **except** the three workflow scripts being wired into the CLI (`mapSpecAngleScan_v4.2.py`, `mapSpecParametricScan.py`, `powderscan_RSM3D_2.1.py`), where pre-existing bugs that would prevent the ported code from working are fixed and explicitly documented (see Task 9 and Task 10).
- `mapSpecAngleScan.py`, `mapSpecAngleScan_v2.py` (superseded angle-scan versions) and `paraviewPlot.py` / `paraviewPlot_tile.py` (require ParaView's `pvpython`, a different interpreter) are moved to `scripts/` **unmodified** and are never imported by anything — not wired into the CLI, not refactored.
- Every task ends with a runnable verification command; run it and read its output before moving to the next task.

---

### Task 1: Scaffold `pyproject.toml` and the `src/` layout

**Files:**
- Create: `pyproject.toml`
- Modify (move): `rsMap3D/` → `src/rsMap3D/` (whole tree, via `git mv`)
- Delete: `setup.py`, `MANIFEST.in`, `.project`, `.pydevproject`
- Modify (rename): `README` → `README.md`

**Interfaces:**
- Produces: an editable-installable `rsMap3D` package at `src/rsMap3D/` that later tasks will further reorganize (pulling `test/`, `docs/`, `anglecalcexamples/`, and most of `resources/` back out in Tasks 2–4). Nothing downstream depends on any new function/class from this task — it's pure scaffolding.

- [ ] **Step 1: Move the whole package into `src/`**

```bash
mkdir -p src
git mv rsMap3D src/rsMap3D
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "rsMap3D"
version = "1.3.1"
description = "Python program to map x-ray diffraction data into a reciprocal space map"
readme = "README.md"
license = {file = "LICENSE"}
authors = [
    {name = "John Hammonds"},
    {name = "Christian Schleputz"},
]
requires-python = ">=3.9"
dependencies = [
    "PyQt5",
    "vtk",
    "numpy",
    "xrayutilities",
    "h5py",
    "hdf5plugin",
    "matplotlib",
    "spec2nexus",
    "pillow",
]

[project.optional-dependencies]
xpcs = ["pyepics"]
dev = ["pytest"]

[project.scripts]
rsMap3D = "rsMap3D.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
rsMap3D = ["resources/*.xml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

(`rsMap3D.cli:main` doesn't exist yet — it's created in Task 7. `[project.scripts]` just needs to parse; it isn't resolved until an editable install is (re)run.)

- [ ] **Step 3: Remove the old packaging files and stale IDE metadata**

```bash
git rm setup.py MANIFEST.in .project .pydevproject
```

- [ ] **Step 4: Rename README to README.md**

```bash
git mv README README.md
```

Open `README.md` and add a single `# rsMap3D` heading at the top (it currently starts directly with prose/version history) — no other content changes.

- [ ] **Step 5: Editable-install and verify the package still imports**

```bash
pip install -e .
python -c "import rsMap3D; print(rsMap3D.__version__)"
```

Expected: prints `1.3.1`, no import errors. (PyQt5/vtk/xrayutilities etc. must already be available — use the `d2607_rsmap3d` conda env per `CLAUDE.md`.)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Scaffold pyproject.toml and move rsMap3D package into src/ layout"
```

---

### Task 2: Split `resources/` into package data, test fixtures, and reference scripts

**Files:**
- Move: `src/rsMap3D/resources/{1-idscan,33-id-e,34-id-escan,34-id-escan-compare,config,problemFilesForTesting,spec}/` → `tests/fixtures/`
- Move: `src/rsMap3D/resources/{.rsMap3D,badpixels.txt,ff_data.tif}` → `tests/fixtures/`
- Move: `src/rsMap3D/resources/{powderscan_newRSM3D.py,powderscan_win.py}` → `scripts/`
- Leave in place: `src/rsMap3D/resources/*.xml` (11 files) — these are package data, declared in Task 1's `pyproject.toml`.

**Interfaces:**
- Produces: `tests/fixtures/` — the fixture tree Task 6 points every test's fixture-path constants at. Exact subpaths test code will need: `tests/fixtures/spec/CB_140303A_1.spec`, `tests/fixtures/spec/images/...`, `tests/fixtures/config/rsMap3DLog.test.config`, `tests/fixtures/problemFilesForTesting/*.xml`, `tests/fixtures/1-idscan/*`, `tests/fixtures/33-id-e/*`, `tests/fixtures/34-id-escan/*`, `tests/fixtures/34-id-escan-compare/*`, `tests/fixtures/badpixels.txt`, `tests/fixtures/.rsMap3D`.
- Produces: `src/rsMap3D/resources/` retains only `13BMC_DetectorGeometry_740mm.xml`, `13BMC_Instrument.xml`, `33bmDetectorGeometry.xml`, `33BM-instForXrayutilities-noCircles.xml`, `33BM-instForXrayutilities-noMonitor.xml`, `33BM-instForXrayutilities-noScalingFactor.xml`, `33BM-instForXrayutilities.xml`, `7IDC-instForXrayutilitiesFixWrongValuesChiPhi.xml`, `7IDC-instForXrayutilities.xml`, `8IDDetectorGeometry.xml`, `8-ID-instForXrayUtilities.xml` — Task 6 and Task 8 locate these via `importlib.resources.files("rsMap3D") / "resources" / "<name>.xml"`.

- [ ] **Step 1: Move test-fixture subdirectories**

```bash
mkdir -p tests/fixtures
git mv src/rsMap3D/resources/1-idscan tests/fixtures/1-idscan
git mv src/rsMap3D/resources/33-id-e tests/fixtures/33-id-e
git mv src/rsMap3D/resources/34-id-escan tests/fixtures/34-id-escan
git mv src/rsMap3D/resources/34-id-escan-compare tests/fixtures/34-id-escan-compare
git mv src/rsMap3D/resources/config tests/fixtures/config
git mv src/rsMap3D/resources/problemFilesForTesting tests/fixtures/problemFilesForTesting
git mv src/rsMap3D/resources/spec tests/fixtures/spec
```

- [ ] **Step 2: Move remaining loose test-fixture files**

```bash
git mv src/rsMap3D/resources/badpixels.txt tests/fixtures/badpixels.txt
git mv src/rsMap3D/resources/ff_data.tif tests/fixtures/ff_data.tif
git mv src/rsMap3D/resources/.rsMap3D tests/fixtures/.rsMap3D
```

- [ ] **Step 3: Move the two orphaned reference scripts to `scripts/`**

```bash
mkdir -p scripts
git mv src/rsMap3D/resources/powderscan_newRSM3D.py scripts/powderscan_newRSM3D.py
git mv src/rsMap3D/resources/powderscan_win.py scripts/powderscan_win.py
```

- [ ] **Step 4: Verify only the 11 package-data XML files remain**

```bash
ls src/rsMap3D/resources/
```

Expected: exactly the 11 `*.xml` files listed in this task's Interfaces section, nothing else.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Split resources/ into package data (src/rsMap3D/resources) and test fixtures (tests/fixtures)"
```

---

### Task 3: Move `docs/` out of the package, drop committed build output

**Files:**
- Move: `src/rsMap3D/docs/` → `docs/`
- Delete (untrack): `docs/build/`
- Modify: `.gitignore`

**Interfaces:** None — pure documentation relocation, nothing else in the codebase references `docs/`.

- [ ] **Step 1: Move the docs tree**

```bash
git mv src/rsMap3D/docs docs
```

- [ ] **Step 2: Untrack the generated build output**

```bash
git rm -r --cached docs/build
rm -rf docs/build
```

- [ ] **Step 3: Add `docs/build/` to `.gitignore`**

Current `.gitignore` content:
```
# .gitignore for rsMap3D
*.pyc
.DS_Store
```

New content:
```
# .gitignore for rsMap3D
*.pyc
.DS_Store
docs/build/
```

- [ ] **Step 4: Verify**

```bash
git status --short docs/
```

Expected: `docs/build/` no longer appears as tracked; the rest of `docs/` shows as renamed (`R`) from the old `src/rsMap3D/docs/...` paths.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Move docs/ out of the package; stop tracking generated docs/build/"
```

---

### Task 4: `anglecalcexamples/` — SUPERSEDED, stays inside the package

**Original plan:** move `src/rsMap3D/anglecalcexamples/` → `examples/anglecalcexamples/`, on the assumption that nothing imports it.

**What actually happened during execution:** the move was implemented and reviewed clean, but verification turned up `tests/fixtures/33-id-e/33IDE_sixc.xml` referencing `module="rsMap3D.anglecalcexamples.sumgammamu"` — the real `<sampleAngleMapFunction>` plugin mechanism (`Sector33SpecDataSource.py` and other sector data sources `importlib.import_module()` that exact dotted path at runtime). Moving the subpackage off the Python import path would silently break any deployed instrument config using it. The move was reverted: `anglecalcexamples/` stays at `src/rsMap3D/anglecalcexamples/`, shipping with the installed package. No top-level `examples/` directory is created. See the design spec's decision 9 for the corrected rationale.

No further action needed for this task — it is complete as of the revert commit.

---

### Task 5: Move `Scripts/` to `scripts/`, drop the old GUI wrapper

**Files:**
- Move: `Scripts/mapSpecAngleScan.py` → `scripts/mapSpecAngleScan.py`
- Move: `Scripts/mapSpecAngleScan_v2.py` → `scripts/mapSpecAngleScan_v2.py`
- Move: `Scripts/mapSpecAngleScan_v4.2.py` → `scripts/mapSpecAngleScan_v4.2.py` (temporary — deleted in Task 8 once its logic is extracted)
- Move: `Scripts/mapSpecParametricScan.py` → `scripts/mapSpecParametricScan.py` (temporary — deleted in Task 9)
- Move: `Scripts/powderscan_RSM3D_2.1.py` → `scripts/powderscan_RSM3D_2.1.py` (temporary — deleted in Task 10)
- Move: `Scripts/paraviewPlot.py` → `scripts/paraview/paraviewPlot.py`
- Move: `Scripts/paraviewPlot_tile.py` → `scripts/paraview/paraviewPlot_tile.py`
- Move: `Scripts/rsmconfig_v4.2_lsfo_IntegerPeaks.json` → `scripts/rsmconfig_v4.2_lsfo_IntegerPeaks.json`
- Move: `Scripts/rsmconfig_v4.2_lsfo_IntegerPeaks_batch.json` → `scripts/rsmconfig_v4.2_lsfo_IntegerPeaks_batch.json`
- Delete: `Scripts/rsMap3D`, `Scripts/rsMap3D.bat` (replaced by the `[project.scripts]` entry point from Task 1, wired up in Task 7)

**Interfaces:** None yet — Tasks 8–10 will `git rm` three of these files once their logic lives in `src/rsMap3D/workflows/`.

- [ ] **Step 1: Move the reference-only and paraview scripts**

```bash
mkdir -p scripts/paraview
git mv Scripts/mapSpecAngleScan.py scripts/mapSpecAngleScan.py
git mv Scripts/mapSpecAngleScan_v2.py scripts/mapSpecAngleScan_v2.py
git mv Scripts/paraviewPlot.py scripts/paraview/paraviewPlot.py
git mv Scripts/paraviewPlot_tile.py scripts/paraview/paraviewPlot_tile.py
```

- [ ] **Step 2: Move the JSON sample configs**

```bash
git mv Scripts/rsmconfig_v4.2_lsfo_IntegerPeaks.json scripts/rsmconfig_v4.2_lsfo_IntegerPeaks.json
git mv Scripts/rsmconfig_v4.2_lsfo_IntegerPeaks_batch.json scripts/rsmconfig_v4.2_lsfo_IntegerPeaks_batch.json
```

- [ ] **Step 3: Move the three scripts that will become CLI subcommands (temporary location)**

```bash
git mv Scripts/mapSpecAngleScan_v4.2.py scripts/mapSpecAngleScan_v4.2.py
git mv Scripts/mapSpecParametricScan.py scripts/mapSpecParametricScan.py
git mv Scripts/powderscan_RSM3D_2.1.py scripts/powderscan_RSM3D_2.1.py
```

- [ ] **Step 4: Drop the old GUI launcher wrappers**

```bash
git rm Scripts/rsMap3D Scripts/rsMap3D.bat
rmdir Scripts
```

- [ ] **Step 5: Verify**

```bash
ls Scripts 2>&1 | grep -q "No such file" && echo "Scripts/ removed" || echo "Scripts/ still exists — check for leftover files"
ls scripts/
```

Expected: `Scripts/ removed`; `scripts/` lists the moved `.py`/`.json` files plus a `paraview/` subdirectory.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Move Scripts/ to scripts/; drop GUI launcher wrappers superseded by console_scripts"
```

---

### Task 6: Migrate the test suite to `tests/` on pytest

**Files:**
- Move + rename every file under `src/rsMap3D/test/` to the corresponding `tests/` path with a `test_*.py` name (see mapping table below).
- Delete: `src/rsMap3D/test/datasource/detectorgeometry/__init__.pyc`, `.../testdetectorgeometryforescan.pyc` (git-tracked Python-2 bytecode, not moved).
- Modify: fixture path constants inside the moved files (see per-file diffs below).

**File mapping (old → new):**

| Old path | New path |
|---|---|
| `src/rsMap3D/test/__init__.py` | `tests/__init__.py` |
| `src/rsMap3D/test/config/__init__.py` | `tests/config/__init__.py` |
| `src/rsMap3D/test/config/testrsmap3dconfig.py` | `tests/config/test_rsmap3dconfig.py` |
| `src/rsMap3D/test/datasource/__init__.py` | `tests/datasource/__init__.py` |
| `src/rsMap3D/test/datasource/testabstractxrayutilitiesdatasource.py` | `tests/datasource/test_abstractxrayutilitiesdatasource.py` |
| `src/rsMap3D/test/datasource/testbadpixelfile.py` | `tests/datasource/test_badpixelfile.py` |
| `src/rsMap3D/test/datasource/testdetectorgeometryforxrayutilitiesreader.py` | `tests/datasource/test_detectorgeometryforxrayutilitiesreader.py` |
| `src/rsMap3D/test/datasource/testinstforxrayutilitiesreader.py` | `tests/datasource/test_instforxrayutilitiesreader.py` |
| `src/rsMap3D/test/datasource/testsector33specdatasource.py` | `tests/datasource/test_sector33specdatasource.py` |
| `src/rsMap3D/test/datasource/testsector34nexusescan.py` | `tests/datasource/test_sector34nexusescan.py` |
| `src/rsMap3D/test/datasource/detectorgeometry/__init__.py` | `tests/datasource/detectorgeometry/__init__.py` |
| `src/rsMap3D/test/datasource/detectorgeometry/testdetectorgeometryforescan.py` | `tests/datasource/detectorgeometry/test_detectorgeometryforescan.py` |
| `src/rsMap3D/test/datasource/sector1/__init__.py` | `tests/datasource/sector1/__init__.py` |
| `src/rsMap3D/test/datasource/sector1/testsector1highenergydiffds.py` | `tests/datasource/sector1/test_sector1highenergydiffds.py` |
| `src/rsMap3D/test/gui/__init__.py` | `tests/gui/__init__.py` |
| `src/rsMap3D/test/gui/testScanForm.py` | `tests/gui/test_scan_form.py` |
| `src/rsMap3D/test/gui/input/__init__.py` | `tests/gui/input/__init__.py` |
| `src/rsMap3D/test/gui/input/test_s33specscanfileform.py` | `tests/gui/input/test_s33specscanfileform.py` (name already conforms) |
| `src/rsMap3D/test/gui/output/__init__.py` | `tests/gui/output/__init__.py` |
| `src/rsMap3D/test/gui/output/test_abstractgridoutputview.py` | `tests/gui/output/test_abstractgridoutputview.py` (already conforms) |
| `src/rsMap3D/test/gui/output/test_abstractoutputview.py` | `tests/gui/output/test_abstractoutputview.py` (already conforms) |

**Interfaces:** None — no production code depends on test file names/locations.

- [ ] **Step 1: Move everything with `git mv`**

```bash
mkdir -p tests/config tests/datasource/detectorgeometry tests/datasource/sector1 \
         tests/gui/input tests/gui/output

git mv src/rsMap3D/test/__init__.py tests/__init__.py
git mv src/rsMap3D/test/config/__init__.py tests/config/__init__.py
git mv src/rsMap3D/test/config/testrsmap3dconfig.py tests/config/test_rsmap3dconfig.py
git mv src/rsMap3D/test/datasource/__init__.py tests/datasource/__init__.py
git mv src/rsMap3D/test/datasource/testabstractxrayutilitiesdatasource.py tests/datasource/test_abstractxrayutilitiesdatasource.py
git mv src/rsMap3D/test/datasource/testbadpixelfile.py tests/datasource/test_badpixelfile.py
git mv src/rsMap3D/test/datasource/testdetectorgeometryforxrayutilitiesreader.py tests/datasource/test_detectorgeometryforxrayutilitiesreader.py
git mv src/rsMap3D/test/datasource/testinstforxrayutilitiesreader.py tests/datasource/test_instforxrayutilitiesreader.py
git mv src/rsMap3D/test/datasource/testsector33specdatasource.py tests/datasource/test_sector33specdatasource.py
git mv src/rsMap3D/test/datasource/testsector34nexusescan.py tests/datasource/test_sector34nexusescan.py
git mv src/rsMap3D/test/datasource/detectorgeometry/__init__.py tests/datasource/detectorgeometry/__init__.py
git mv src/rsMap3D/test/datasource/detectorgeometry/testdetectorgeometryforescan.py tests/datasource/detectorgeometry/test_detectorgeometryforescan.py
git rm src/rsMap3D/test/datasource/detectorgeometry/__init__.pyc src/rsMap3D/test/datasource/detectorgeometry/testdetectorgeometryforescan.pyc
git mv src/rsMap3D/test/datasource/sector1/__init__.py tests/datasource/sector1/__init__.py
git mv src/rsMap3D/test/datasource/sector1/testsector1highenergydiffds.py tests/datasource/sector1/test_sector1highenergydiffds.py
git mv src/rsMap3D/test/gui/__init__.py tests/gui/__init__.py
git mv src/rsMap3D/test/gui/testScanForm.py tests/gui/test_scan_form.py
git mv src/rsMap3D/test/gui/input/__init__.py tests/gui/input/__init__.py
git mv src/rsMap3D/test/gui/input/test_s33specscanfileform.py tests/gui/input/test_s33specscanfileform.py
git mv src/rsMap3D/test/gui/output/__init__.py tests/gui/output/__init__.py
git mv src/rsMap3D/test/gui/output/test_abstractgridoutputview.py tests/gui/output/test_abstractgridoutputview.py
git mv src/rsMap3D/test/gui/output/test_abstractoutputview.py tests/gui/output/test_abstractoutputview.py
rmdir src/rsMap3D/test/gui/output src/rsMap3D/test/gui/input src/rsMap3D/test/gui \
      src/rsMap3D/test/datasource/sector1 src/rsMap3D/test/datasource/detectorgeometry \
      src/rsMap3D/test/datasource src/rsMap3D/test/config src/rsMap3D/test
```

- [ ] **Step 2: Fix `tests/config/test_rsmap3dconfig.py`**

Replace:
```python
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BAD_FILE_DIRECTORY = os.path.join(THIS_DIR,
                                  "../../resources/problemFilesForTesting/")
GOOD_FILE_DIRECTORY = os.path.join(THIS_DIR, "../../resources/")
```
with:
```python
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BAD_FILE_DIRECTORY = os.path.join(THIS_DIR,
                                  "../fixtures/problemFilesForTesting/")
GOOD_FILE_DIRECTORY = os.path.join(THIS_DIR, "../fixtures/")
```

- [ ] **Step 3: Fix `tests/datasource/test_badpixelfile.py`**

Replace:
```python
        fileName = os.path.join(THIS_DIR,
                               "../../resources/badpixels.txt") 
```
with:
```python
        fileName = os.path.join(THIS_DIR,
                               "../fixtures/badpixels.txt")
```

- [ ] **Step 4: Fix `tests/datasource/test_detectorgeometryforxrayutilitiesreader.py`**

This file mixes package data (root XML) and test fixtures (`problemFilesForTesting/`), and has a Python 2 `print` statement. Replace lines 14–28:
```python
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
configDir = os.path.join(THIS_DIR, '../../resources/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print logConfigFile
logging.config.fileConfig(logConfigFile)
logger = logging.getLogger(LOGGER_NAME)



FILE_BASE_DIR = os.path.join(THIS_DIR, '../../resources/')
BAD_FILE_DIR = FILE_BASE_DIR + 'problemFilesForTesting/'
BAD_FILE_NO_DETECTOR_LIST = BAD_FILE_DIR + 'detectorGeometryNoDetectorList.xml'
BAD_FILE_NO_DETECTOR = BAD_FILE_DIR + 'detectorGeometryNoDetector.xml'
DETECTOR_NAME = 'Pilatus'
GOOD_FILE_NAME = FILE_BASE_DIR + '33bmDetectorGeometry.xml'
```
with:
```python
import importlib.resources

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
configDir = os.path.join(THIS_DIR, '../fixtures/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print(logConfigFile)
logging.config.fileConfig(logConfigFile)
logger = logging.getLogger(LOGGER_NAME)



BAD_FILE_DIR = os.path.join(THIS_DIR, '../fixtures/problemFilesForTesting/')
BAD_FILE_NO_DETECTOR_LIST = BAD_FILE_DIR + 'detectorGeometryNoDetectorList.xml'
BAD_FILE_NO_DETECTOR = BAD_FILE_DIR + 'detectorGeometryNoDetector.xml'
DETECTOR_NAME = 'Pilatus'
GOOD_FILE_NAME = str(importlib.resources.files('rsMap3D') / 'resources' / '33bmDetectorGeometry.xml')
```
Also replace the deprecated alias on line 58 (`assertNotEquals` was removed in Python 3.12):
```python
        self.assertNotEquals(detector, None, "getDetectorById")
```
with:
```python
        self.assertNotEqual(detector, None, "getDetectorById")
```

- [ ] **Step 5: Fix `tests/datasource/test_instforxrayutilitiesreader.py`**

Replace the `setUp` block:
```python
    def setUp(self):
        self.config = InstForXrayutilitiesReader( \
                 os.path.join(THIS_DIR, 
                              '../../resources/33BM-instForXrayutilities.xml'))
        self.config2 = InstForXrayutilitiesReader( \
                 os.path.join(THIS_DIR, 
                      '../../resources/33BM-instForXrayutilities-noMonitor.xml'))
        self.config3 = InstForXrayutilitiesReader( \
                 os.path.join(THIS_DIR, 
                      '../../resources/33BM-instForXrayutilities-noCircles.xml'))
        self.config4 = InstForXrayutilitiesReader( \
                 os.path.join(THIS_DIR, 
                      '../../resources/33BM-instForXrayutilities-noScalingFactor.xml'))
        self.config5 = InstForXrayutilitiesReader( \
                 os.path.join(THIS_DIR, 
                      '../../resources/13BMC_Instrument.xml'))
        self.config6 = InstForXrayutilitiesReader( \
                 os.path.join(THIS_DIR, 
                      '../../resources/7IDC-instForXrayutilitiesFixWrongValuesChiPhi.xml'))
```
with:
```python
    def setUp(self):
        resources_dir = importlib.resources.files('rsMap3D') / 'resources'
        self.config = InstForXrayutilitiesReader(
                 str(resources_dir / '33BM-instForXrayutilities.xml'))
        self.config2 = InstForXrayutilitiesReader(
                 str(resources_dir / '33BM-instForXrayutilities-noMonitor.xml'))
        self.config3 = InstForXrayutilitiesReader(
                 str(resources_dir / '33BM-instForXrayutilities-noCircles.xml'))
        self.config4 = InstForXrayutilitiesReader(
                 str(resources_dir / '33BM-instForXrayutilities-noScalingFactor.xml'))
        self.config5 = InstForXrayutilitiesReader(
                 str(resources_dir / '13BMC_Instrument.xml'))
        self.config6 = InstForXrayutilitiesReader(
                 str(resources_dir / '7IDC-instForXrayutilitiesFixWrongValuesChiPhi.xml'))
```
Add `import importlib.resources` to the top of the file (alongside the existing `import os`), and replace:
```python
PROBLEM_FILES_DIR = os.path.join(THIS_DIR,  
                                 '../../resources/problemFilesForTesting/')
```
with:
```python
PROBLEM_FILES_DIR = os.path.join(THIS_DIR,
                                 '../fixtures/problemFilesForTesting/')
```
Finally, replace every deprecated `self.assertEquals(` with `self.assertEqual(` throughout the file (18 occurrences — search-and-replace the exact string `assertEquals(` → `assertEqual(`, there is no other use of `assertEquals` with different intent in this file).

- [ ] **Step 6: Fix `tests/datasource/test_sector33specdatasource.py`**

Replace:
```python
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(THIS_DIR, "../../resources/spec")
PROJECT_NAME = "CB_140303A_1"
PROJECT_EXT = ".spec"
INST_CONFIG_1 = os.path.join(THIS_DIR, 
                             "../../resources/33BM-instForXrayutilities.xml")
DET_CONFIG = os.path.join(THIS_DIR, "../../resources/33bmDetectorGeometry.xml")
CURRENT_DETECTOR = "Pilatus"
configDir = os.path.join(THIS_DIR, '../../resources/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print logConfigFile
logging.config.fileConfig(logConfigFile)
```
with:
```python
import importlib.resources

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(THIS_DIR, "../fixtures/spec")
PROJECT_NAME = "CB_140303A_1"
PROJECT_EXT = ".spec"
_RESOURCES_DIR = importlib.resources.files('rsMap3D') / 'resources'
INST_CONFIG_1 = str(_RESOURCES_DIR / "33BM-instForXrayutilities.xml")
DET_CONFIG = str(_RESOURCES_DIR / "33bmDetectorGeometry.xml")
CURRENT_DETECTOR = "Pilatus"
configDir = os.path.join(THIS_DIR, '../fixtures/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print(logConfigFile)
logging.config.fileConfig(logConfigFile)
```

- [ ] **Step 7: Fix `tests/datasource/test_sector34nexusescan.py`**

Replace:
```python
FILE_BASE_DIR = os.path.join(THIS_DIR,'../../resources/34-id-escan/')
```
with:
```python
FILE_BASE_DIR = os.path.join(THIS_DIR,'../fixtures/34-id-escan/')
```
Replace (note the missing `/` typo in the original, fixed here since this line is being rewritten anyway to point at the new fixture path):
```python
        self.projectDir = os.path.join(THIS_DIR, 
                                       "../..resources/34-id-escan-compare")
        self.projectName = ""
        self.projectExtension = ".h5"
        self.detConfigFile = os.path.join(THIS_DIR,
          "../../resources/34-id-escan-compare/geoN_2016-02-17_18-11-38.xml")
```
with:
```python
        self.projectDir = os.path.join(THIS_DIR,
                                       "../fixtures/34-id-escan-compare")
        self.projectName = ""
        self.projectExtension = ".h5"
        self.detConfigFile = os.path.join(THIS_DIR,
          "../fixtures/34-id-escan-compare/geoN_2016-02-17_18-11-38.xml")
```
Replace every bare `print X` statement in `testComparePixel2XYZ` with `print(X)` — there are 30 such lines (55–108). Apply this mechanical transform to each:
```python
        print self.datasource.rho
        print "+++++++++++++"
        print self.datasource.rho[0]
        print self.datasource.rho[1]
        print self.datasource.rho[2]
        print "+++++++++++++"
        print self.datasource.rho[:,0]
        print self.datasource.rho[:,1]
        print self.datasource.rho[:,2]
        
        print self.datasource.detectorROI
        xIndexArray = range(self.datasource.detectorROI[0], self.datasource.detectorROI[1] +1)
        yIndexArray = range(self.datasource.detectorROI[2], self.datasource.detectorROI[3] +1)

        import numpy as np
        print "calculate from mesh"
        indexMesh = np.meshgrid(xIndexArray, yIndexArray)
        qpxyz = self.datasource.pixel2q_2(indexMesh, None)
        print "qpxyz.shape"
        print qpxyz.shape
        print "qpxyz[0]"
        print qpxyz[0]
        print qpxyz[0].shape
        print "qpxyz[1]"
        print qpxyz[1]
        print qpxyz[1].shape
        print "qpxyz[2]"
        print qpxyz[2]
        print qpxyz[2].shape
        
        arraySize = [len(xIndexArray), len(yIndexArray)]
       
        print "calculate from loop"
```
becomes:
```python
        print(self.datasource.rho)
        print("+++++++++++++")
        print(self.datasource.rho[0])
        print(self.datasource.rho[1])
        print(self.datasource.rho[2])
        print("+++++++++++++")
        print(self.datasource.rho[:,0])
        print(self.datasource.rho[:,1])
        print(self.datasource.rho[:,2])
        
        print(self.datasource.detectorROI)
        xIndexArray = range(self.datasource.detectorROI[0], self.datasource.detectorROI[1] +1)
        yIndexArray = range(self.datasource.detectorROI[2], self.datasource.detectorROI[3] +1)

        import numpy as np
        print("calculate from mesh")
        indexMesh = np.meshgrid(xIndexArray, yIndexArray)
        qpxyz = self.datasource.pixel2q_2(indexMesh, None)
        print("qpxyz.shape")
        print(qpxyz.shape)
        print("qpxyz[0]")
        print(qpxyz[0])
        print(qpxyz[0].shape)
        print("qpxyz[1]")
        print(qpxyz[1])
        print(qpxyz[1].shape)
        print("qpxyz[2]")
        print(qpxyz[2])
        print(qpxyz[2].shape)
        
        arraySize = [len(xIndexArray), len(yIndexArray)]
       
        print("calculate from loop")
```
and:
```python
        print "qpx"
        print self.qpx
        print self.qpx.shape
        print "qpy"
        print self.qpy
        print self.qpy.shape
        print "qpz"
        print self.qpz
        print self.qpz.shape
```
becomes:
```python
        print("qpx")
        print(self.qpx)
        print(self.qpx.shape)
        print("qpy")
        print(self.qpy)
        print(self.qpy.shape)
        print("qpz")
        print(self.qpz)
        print(self.qpz.shape)
```

- [ ] **Step 8: Fix `tests/datasource/detectorgeometry/test_detectorgeometryforescan.py`**

Replace:
```python
configDir = os.path.join(THIS_DIR, '../../../resources/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print logConfigFile
logging.config.fileConfig(logConfigFile)
logger = logging.getLogger(LOGGER_NAME)


FILE_BASE_DIR = os.path.join(THIS_DIR, '../../../resources/34-id-escan/')
```
with:
```python
configDir = os.path.join(THIS_DIR, '../../fixtures/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print(logConfigFile)
logging.config.fileConfig(logConfigFile)
logger = logging.getLogger(LOGGER_NAME)


FILE_BASE_DIR = os.path.join(THIS_DIR, '../../fixtures/34-id-escan/')
```
Replace the Python 2 `<>` operator:
```python
        if config <> None:
```
with:
```python
        if config != None:
```

- [ ] **Step 9: Fix `tests/datasource/sector1/test_sector1highenergydiffds.py`**

Replace:
```python
configDir = os.path.join(THIS_DIR, '../../../resources/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print logConfigFile
logging.config.fileConfig(logConfigFile)
logger = logging.getLogger(LOGGER_NAME)
PAR_FILE1 = os.path.join(THIS_DIR, \
                         "../../../resources/1-idscan/fastpar_startup_oct16_FF1.par")
PAR_FILE2 = os.path.join(THIS_DIR, \
                         "../../../resources/1-idscan/fastpar_startup_oct16_FF1_with_comments.par")
PAR_FILE3 = os.path.join(THIS_DIR, \
                         "../../../resources/1-idscan/fastpar_startup_oct16_FF1_with_blanks.par")
```
with:
```python
configDir = os.path.join(THIS_DIR, '../../fixtures/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print(logConfigFile)
logging.config.fileConfig(logConfigFile)
logger = logging.getLogger(LOGGER_NAME)
PAR_FILE1 = os.path.join(THIS_DIR, \
                         "../../fixtures/1-idscan/fastpar_startup_oct16_FF1.par")
PAR_FILE2 = os.path.join(THIS_DIR, \
                         "../../fixtures/1-idscan/fastpar_startup_oct16_FF1_with_comments.par")
PAR_FILE3 = os.path.join(THIS_DIR, \
                         "../../fixtures/1-idscan/fastpar_startup_oct16_FF1_with_blanks.par")
```
Replace the deprecated alias:
```python
        self.assertEquals(availableScans, [3,])
```
with:
```python
        self.assertEqual(availableScans, [3,])
```

- [ ] **Step 10: Add pytest as a dev dependency and configure it** (already declared in `pyproject.toml` from Task 1 — just install it now)

```bash
pip install -e ".[dev]"
```

- [ ] **Step 11: Collect the whole suite (imports only, no display needed for collection)**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ --collect-only -q
```

Expected: every test file is collected with no `SyntaxError`/`ImportError`/`AttributeError`; the count of collected items is printed with no "errors" section. (Some individual tests may still fail at *run* time for reasons unrelated to this migration — e.g. missing sample data variants, EPICS PVs, or a real display — that's expected and out of scope; this step only proves the *files* are valid pytest modules.)

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "Migrate rsMap3D/test to tests/ on pytest: rename to test_*.py, fix Python 2/3.12-removed-alias syntax, repoint fixture paths"
```

---

### Task 7: Add the `rsMap3D` CLI (GUI launcher as `console_scripts`)

**Files:**
- Modify: `src/rsMap3D/rsmEdit.py`
- Create: `src/rsMap3D/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `rsMap3D.rsmEdit.main() -> None` — launches the existing GUI (same body as today's `if __name__ == "__main__":` block).
- Produces: `rsMap3D.cli.main(argv: list[str] | None = None) -> None` — argparse entry point. Subcommands `gui` (default), `map-angle-scan CONFIG_PATH`, `map-parametric-scan CONFIG_PATH`, `powder-scan CONFIG_PATH`. Tasks 8–10 add the three workflow dispatch branches' target modules (`rsMap3D.workflows.angle_scan`, `.parametric_scan`, `.powder_scan`), each exposing a `run(config: dict) -> None` function — `cli.py` is written now assuming those modules exist and is verified against them once Tasks 8–10 create them.

- [ ] **Step 1: Add `main()` to `rsmEdit.py`**

In `src/rsMap3D/rsmEdit.py`, replace:
```python
def ctrlCHandler(signal, frame):
    qtWidgets.QApplication.closeAllWindows()
    
if __name__ == "__main__":
    #This line allows CTRL_C to work with PyQt.
    logger.debug(METHOD_ENTER_STR)
    signal.signal(signal.SIGINT, ctrlCHandler)
    app = qtWidgets.QApplication(sys.argv)
    mainForm = MainDialog()
    mainForm.show()
    #timer allows Python interupts to work
    timer = qtCore.QTimer()
    timer.start(1000)
    timer.timeout.connect(lambda: None)
    app.exec_()
```
with:
```python
def ctrlCHandler(signal, frame):
    qtWidgets.QApplication.closeAllWindows()

def main():
    '''
    Launch the rsMap3D GUI. Entry point for `rsMap3D` / `rsMap3D gui`.
    '''
    #This line allows CTRL_C to work with PyQt.
    logger.debug(METHOD_ENTER_STR)
    signal.signal(signal.SIGINT, ctrlCHandler)
    app = qtWidgets.QApplication(sys.argv)
    mainForm = MainDialog()
    mainForm.show()
    #timer allows Python interupts to work
    timer = qtCore.QTimer()
    timer.start(1000)
    timer.timeout.connect(lambda: None)
    app.exec_()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the failing CLI test**

Create `tests/test_cli.py`:
```python
'''
 Copyright (c) 2026, UChicago Argonne, LLC
 See LICENSE file.
'''
import json

from rsMap3D import cli


def test_no_subcommand_launches_gui(monkeypatch):
    calls = []
    monkeypatch.setattr("rsMap3D.rsmEdit.main", lambda: calls.append("gui"))
    cli.main([])
    assert calls == ["gui"]


def test_gui_subcommand_launches_gui(monkeypatch):
    calls = []
    monkeypatch.setattr("rsMap3D.rsmEdit.main", lambda: calls.append("gui"))
    cli.main(["gui"])
    assert calls == ["gui"]


def test_map_angle_scan_dispatches_with_parsed_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("rsMap3D.workflows.angle_scan.run", lambda config: calls.append(config))
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps({"project_dir": "/tmp/x"}))
    cli.main(["map-angle-scan", str(config_path)])
    assert calls == [{"project_dir": "/tmp/x"}]


def test_map_parametric_scan_dispatches_with_parsed_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("rsMap3D.workflows.parametric_scan.run", lambda config: calls.append(config))
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps({"scan_list": ["1"]}))
    cli.main(["map-parametric-scan", str(config_path)])
    assert calls == [{"scan_list": ["1"]}]


def test_powder_scan_dispatches_with_parsed_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("rsMap3D.workflows.powder_scan.run", lambda config: calls.append(config))
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps({"datasets": []}))
    cli.main(["powder-scan", str(config_path)])
    assert calls == [{"datasets": []}]
```

- [ ] **Step 3: Run it to verify it fails**

```bash
pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError: No module named 'rsMap3D.cli'` (or collection error) — `cli.py` doesn't exist yet.

- [ ] **Step 4: Create `src/rsMap3D/cli.py`**

```python
'''
 Copyright (c) 2026, UChicago Argonne, LLC
 See LICENSE file.
'''
import argparse
import json


def _load_config(config_path):
    with open(config_path, 'r') as config_file:
        return json.load(config_file)


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="rsMap3D",
        description="rsMap3D: map x-ray scattering images into reciprocal space.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="Launch the rsMap3D GUI (default).")

    angle_scan_parser = subparsers.add_parser(
        "map-angle-scan",
        help="Grid a spec angle scan into a reciprocal space map (Sector 33).",
    )
    angle_scan_parser.add_argument("config_path", help="Path to an rsmconfig.json file.")

    parametric_scan_parser = subparsers.add_parser(
        "map-parametric-scan",
        help="Grid a parametric scan, one output file per image in the scan (Sector 33).",
    )
    parametric_scan_parser.add_argument("config_path", help="Path to a parametric scan config JSON file.")

    powder_scan_parser = subparsers.add_parser(
        "powder-scan",
        help="Reduce spec scans into 1D powder-diffraction curves (Sector 33).",
    )
    powder_scan_parser.add_argument("config_path", help="Path to a powder scan config JSON file.")

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "gui"):
        from rsMap3D.rsmEdit import main as gui_main
        gui_main()
    elif args.command == "map-angle-scan":
        from rsMap3D.workflows import angle_scan
        angle_scan.run(_load_config(args.config_path))
    elif args.command == "map-parametric-scan":
        from rsMap3D.workflows import parametric_scan
        parametric_scan.run(_load_config(args.config_path))
    elif args.command == "powder-scan":
        from rsMap3D.workflows import powder_scan
        powder_scan.run(_load_config(args.config_path))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create the (still-empty) `workflows` package so the imports above resolve**

```bash
mkdir -p src/rsMap3D/workflows
touch src/rsMap3D/workflows/__init__.py
```

Also create empty placeholder modules so `monkeypatch.setattr` in the test above has something to attach to (Tasks 8–10 fill these in):
```bash
touch src/rsMap3D/workflows/angle_scan.py
touch src/rsMap3D/workflows/parametric_scan.py
touch src/rsMap3D/workflows/powder_scan.py
```
Add a one-line `def run(config): raise NotImplementedError` to each of the three new files for now.

- [ ] **Step 6: Run the test to verify it passes**

```bash
pytest tests/test_cli.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 7: Re-install and verify the console script works**

```bash
pip install -e .
rsMap3D --help
```

Expected: argparse help text listing the `gui`, `map-angle-scan`, `map-parametric-scan`, `powder-scan` subcommands, no import errors (PyQt5 is not imported until a `gui`-dispatch actually runs, so `--help` works even in a minimal environment).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "Add rsMap3D CLI (argparse) with a gui subcommand wired to rsmEdit.main()"
```

---

### Task 8: Extract `mapSpecAngleScan_v4.2.py` into `rsMap3D.workflows.angle_scan`

**Files:**
- Create (overwrite placeholder): `src/rsMap3D/workflows/angle_scan.py`
- Delete: `scripts/mapSpecAngleScan_v4.2.py`
- Test: `tests/workflows/__init__.py`, `tests/workflows/test_angle_scan.py`

**Interfaces:**
- Consumes: `rsMap3D.datasource.Sector33SpecDataSource.Sector33SpecDataSource(projectDir, projectName, projectExtension, instConfigFile, detConfigFile, **kwargs)`, `rsMap3D.mappers.gridmapper.QGridMapper(dataSource, outputFileName, outputType=..., nx=..., ny=..., nz=..., transform=..., gridWriter=..., appConfig=...)` — both pre-existing, unchanged.
- Produces: `rsMap3D.workflows.angle_scan.run(config: dict) -> None`. `config` keys: `project_dir`, `config_dir` (or `None` to fall back to `project_dir`), `detector_config`, `instrument_config`, `badpixel_file`, `flat_field` (or `None`), `detector_name`, `binning`, `roi_setting` (or `None`), `nx`, `ny`, `nz`, `grid_range` (or `None`), `use_HKL`, `real_time`, `maxTime_1Scan`, `datasets` (list of `{"spec_file": str, "scan_list": [[str, ...], ...]}` or `{"spec_file": str, "scan_list": None, "scan_range": {...}}`). This is exactly the schema of the existing `Scripts/rsmconfig_v4.2_*.json` sample files.

**Known pre-existing bug fixed during this extraction (found during task review, documented here after the fact — see progress ledger):** the original assigned `dReader = detReader(detectorConfigName)` *after* the `if roi is None:` block that calls `dReader.getDetectorById(...)` — a definition-before-use bug that raised `NameError` for any config with `roi_setting: null`, before the mapper ever ran. This extraction moves the `dReader` assignment above that block, matching the same category of fix already applied to `mapSpecParametricScan.py` (Task 9) and `powderscan_RSM3D_2.1.py` (Task 10): a real, previously-broken code path made to work as evidently intended, documented explicitly rather than silently carried over or silently fixed.

- [ ] **Step 1: Write the failing test**

Create `tests/workflows/__init__.py` (empty) and `tests/workflows/test_angle_scan.py`:
```python
'''
 Copyright (c) 2026, UChicago Argonne, LLC
 See LICENSE file.
'''
import importlib.resources
import os
import shutil

import pytest

from rsMap3D.workflows import angle_scan

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")


class _FakeDataSource:
    instances = []

    def __init__(self, projectDir, projectName, projectExtension,
                 instConfigFile, detConfigFile, **kwargs):
        self.projectDir = projectDir
        self.projectName = projectName
        self.projectExtension = projectExtension
        self.instConfigFile = instConfigFile
        self.detConfigFile = detConfigFile
        self.kwargs = kwargs
        self.currentDetector = None
        _FakeDataSource.instances.append(self)

    def setCurrentDetector(self, name):
        self.currentDetector = name

    def setProgressUpdater(self, updater):
        pass

    def loadSource(self, mapHKL=False):
        self.mapHKL = mapHKL

    def getOverallRanges(self):
        return (0, 1, 0, 1, 0, 1)

    def setRangeBounds(self, bounds):
        self.rangeBounds = bounds


class _FakeGridMapper:
    instances = []

    def __init__(self, dataSource, outputFileName, **kwargs):
        self.dataSource = dataSource
        self.outputFileName = outputFileName
        self.kwargs = kwargs
        _FakeGridMapper.instances.append(self)

    def setProgressUpdater(self, updater):
        pass

    def doMap(self):
        self.mapped = True


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeDataSource.instances.clear()
    _FakeGridMapper.instances.clear()
    yield


@pytest.fixture
def config(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    shutil.copy(
        os.path.join(FIXTURES_DIR, "spec", "CB_140303A_1.spec"),
        project_dir / "CB_140303A_1.spec",
    )
    resources_dir = str(importlib.resources.files("rsMap3D") / "resources")
    return {
        "project_dir": str(project_dir),
        "config_dir": resources_dir,
        "detector_config": "33bmDetectorGeometry.xml",
        "instrument_config": "33BM-instForXrayutilities.xml",
        "badpixel_file": os.path.join(FIXTURES_DIR, "badpixels.txt"),
        "flat_field": None,
        "detector_name": "Pilatus",
        "binning": [1, 1],
        "roi_setting": [1, 487, 1, 195],
        "nx": 10, "ny": 11, "nz": 12,
        "grid_range": None,
        "use_HKL": False,
        "real_time": False,
        "datasets": [
            {"spec_file": "CB_140303A_1.spec", "scan_list": [["1"]]},
        ],
        "maxTime_1Scan": 60,
    }


def test_run_builds_datasource_and_mapper_from_config(monkeypatch, tmp_path, config):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(angle_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(angle_scan, "QGridMapper", _FakeGridMapper)

    angle_scan.run(config)

    assert len(_FakeDataSource.instances) == 1
    ds = _FakeDataSource.instances[0]
    assert ds.projectDir == config["project_dir"]
    assert ds.projectName == "CB_140303A_1"
    assert ds.currentDetector == "Pilatus"
    assert ds.kwargs["roi"] == [1, 487, 1, 195]
    assert ds.mapHKL is False

    assert len(_FakeGridMapper.instances) == 1
    mapper = _FakeGridMapper.instances[0]
    assert mapper.kwargs["nx"] == 10
    assert mapper.kwargs["ny"] == 11
    assert mapper.kwargs["nz"] == 12
    assert mapper.outputFileName.endswith("CB_140303A_1_1_Qxyz.vti")
    assert mapper.mapped is True
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/workflows/test_angle_scan.py -v
```

Expected: `AssertionError` or `NotImplementedError` from the placeholder `run()`.

- [ ] **Step 3: Write `src/rsMap3D/workflows/angle_scan.py`**

```python
'''
 Copyright (c) 2017, UChicago Argonne, LLC
 See LICENSE file.

 Extracted from Scripts/mapSpecAngleScan_v4.2.py so it can be driven from
 rsMap3D's CLI (`rsMap3D map-angle-scan config.json`) instead of being run
 as a standalone, hand-edited script.
'''
import datetime
import logging
import os
import time
from pathlib import Path

from spec2nexus import spec

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.datasource.DetectorGeometryForXrayutilitiesReader import \
    DetectorGeometryForXrayutilitiesReader as detReader
from rsMap3D.datasource.Sector33SpecDataSource import Sector33SpecDataSource
from rsMap3D.gui.rsm3dcommonstrings import BINARY_OUTPUT
from rsMap3D.mappers.gridmapper import QGridMapper
from rsMap3D.mappers.output.vtigridwriter import VTIGridWriter
from rsMap3D.transforms.unitytransform3d import UnityTransform3D
from rsMap3D.utils.srange import srange

logger = logging.getLogger(__name__)
_logging_configured = False


def _configure_console_logging():
    '''
    Add a console handler to the root logger the first time this module is
    used, matching the console output the original standalone script
    produced. Guarded so repeated calls to run() do not add duplicate
    handlers.
    '''
    global _logging_configured
    if _logging_configured:
        return
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(handler)
    _logging_configured = True


def reindex_specfile(fullFilename):
    logger.info('=============================')
    logger.info('  Re-indexing the SPEC file...')
    spec_data = spec.SpecDataFile(fullFilename)
    scansInFile_list = spec_data.getScanNumbers()
    logger.info('  Done. The lastest scan # is %s' % scansInFile_list[-1])
    return scansInFile_list, spec_data


def generateScanLists(inputScanList):
    num_cycles = inputScanList["cycles"]
    scans_in_1_cycle = inputScanList["scans_per_cycle"]
    SetsOfRSM = inputScanList["rsm_sets"]

    scanListTop = []
    for i in range(0, num_cycles):
        for oneSetRSM in SetsOfRSM:
            scan_s = oneSetRSM["start"]
            scan_e = oneSetRSM["end"]
            scans_in_1_rsm = scan_e - scan_s + 1
            scanListTop = scanListTop + \
                ([[f"{x}" if scans_in_1_rsm == 1 else f"{x}-{x+scans_in_1_rsm-1}"] for
                  x in range(scan_s + i * scans_in_1_cycle,
                             scan_e + i * scans_in_1_cycle + 1,
                             scans_in_1_rsm)])
    return scanListTop


def _is_scan_done(specfile_full, curr_scan=1):
    '''
    Poll EPICS PVs at 33-ID-D to check whether a scan has finished. Imports
    epics lazily so that config["real_time"]=False (the common case) does
    not require pyepics to be installed.
    '''
    from epics import PV
    specfile_pv = PV("33idSIS:spec:SPECFileName")
    scann_pv = PV("33idSIS:spec:SCANNUM")
    scanDone_pv = PV("33idSIS:spec:ISSCANDONE")

    if (not scann_pv.wait_for_connection(timeout=2)) \
            or (not scanDone_pv.wait_for_connection(timeout=2)) \
            or (not specfile_pv.wait_for_connection(timeout=2)):
        return -1

    if specfile_full != specfile_pv.char_value:
        return 1
    if curr_scan < scann_pv.value:
        return 1
    elif curr_scan == scann_pv.value:
        if scanDone_pv.value == 1:
            return 1
        else:
            return 0
    else:
        return 0


def checkGridRange(gridRange, fullRange):
    if gridRange is None:
        tmp = fullRange
    elif len(gridRange) != 6:
        tmp = fullRange
    else:
        h_min = max(fullRange[0], min(gridRange[0], gridRange[1]))
        h_max = min(fullRange[1], max(gridRange[0], gridRange[1]))
        k_min = max(fullRange[2], min(gridRange[2], gridRange[3]))
        k_max = min(fullRange[3], max(gridRange[2], gridRange[3]))
        l_min = max(fullRange[4], min(gridRange[4], gridRange[5]))
        l_max = min(fullRange[5], max(gridRange[4], gridRange[5]))
        tmp = h_min, h_max, k_min, k_max, l_min, l_max
    return tmp


def _updateDataSourceProgress(value1, value2):
    logger.info("\t\tDataLoading Progress -- Current set: %.3f%%/%s%%" % (value1, value2))


def _updateMapperProgress(value1):
    logger.info("\t\tMapper Progress -- Current volume: %.3f%%" % (value1))


def run(config):
    '''
    Grid one or more spec angle-scan datasets into reciprocal space maps.
    `config` has the same shape as the rsmconfig.json files consumed by
    the historical Scripts/mapSpecAngleScan_v4.2.py script.
    '''
    _configure_console_logging()

    startTime = datetime.datetime.now()
    with open('time.log', 'a') as time_log:
        time_log.write(f'Start: {startTime}\n')

    projectDir = config["project_dir"]
    configDir = config["config_dir"]
    if configDir is None:
        configDir = projectDir

    detectorConfigName = os.path.join(configDir, config["detector_config"])
    instConfigName = os.path.join(configDir, config["instrument_config"])
    badPixelFile = os.path.join(configDir, config["badpixel_file"])
    flatfieldFile = config["flat_field"]

    detectorName = config["detector_name"]
    bin = config["binning"]
    roi = config["roi_setting"]
    nx = config["nx"]
    ny = config["ny"]
    nz = config["nz"]
    gridRange_input = config["grid_range"]
    mapHKL = config["use_HKL"]
    realtime_flag = config["real_time"]

    datasets = config["datasets"]

    if not os.path.exists(detectorConfigName):
        raise Exception("Detector Config file does not exist: %s" %
                        detectorConfigName)
    if not os.path.exists(instConfigName):
        raise Exception("Instrument Config file does not exist: %s" %
                        instConfigName)
    if not os.path.exists(badPixelFile):
        raise Exception("Bad Pixel file does not exist: %s" %
                        badPixelFile)
    if not (flatfieldFile is None):
        flatfieldFile = os.path.join(configDir, flatfieldFile)
        if not os.path.exists(flatfieldFile):
            raise Exception("Flat field file does not exist: %s" %
                            flatfieldFile)

    dReader = detReader(detectorConfigName)

    if roi is None:
        detector = dReader.getDetectorById(detectorName)
        nPixels = dReader.getNpixels(detector)
        roi = [1, nPixels[0], 1, nPixels[1]]
    logger.info("ROI: %s " % roi)

    for idx, dataset in enumerate(datasets, 1):
        specFile = dataset["spec_file"]
        scanListTop = dataset["scan_list"]

        if scanListTop is None:
            inputScanList = dataset["scan_range"]
            scanListTop = generateScanLists(inputScanList)

        specfile_full = os.path.join(projectDir, specFile)
        if not os.path.exists(specfile_full):
            print(f"File not found.  Please check the path and name {specFile} is correct.")
            print(f"Moving on...in a couple of seconds. ")
            time.sleep(2)
            continue

        specName, specExt = os.path.splitext(specFile)
        outputFilePath = os.path.join(projectDir,
                "analysis_runtime", specName)
        Path(outputFilePath).mkdir(parents=True, exist_ok=True)

        logger.info('=============================')
        logger.info(f"SPEC file #{idx}: {specfile_full}")
        logger.info(f"Generated Scan List #{idx}: {scanListTop}")

        scansInFile_list, spec_data = reindex_specfile(specfile_full)

        for scanList1 in scanListTop:
            outputFileName = os.path.join(outputFilePath,
                f"{specName}_{str(scanList1[0])}")

            if mapHKL == True:
                outputFileName += '_hkl.vti'
            else:
                outputFileName += '_Qxyz.vti'

            appConfig = RSMap3DConfigParser()

            scanRange = []
            for scans in scanList1:
                scanRange += srange(scans).list()
            logger.info(f"  --------------------------------")
            logger.info("scanRange %s" % scanRange)

            curr_scan = max(scanRange)
            _accu = 1
            last_len = 0
            while realtime_flag:
                _scanDone_flag = _is_scan_done(specfile_full, curr_scan)
                if _scanDone_flag == 1:
                    break
                elif _scanDone_flag == 0:
                    sleep_time = 5
                else:
                    if not (str(curr_scan) in scansInFile_list):
                        sleep_time = _accu * 5
                        logger.info('  Scan #%d not available yet.  \
                            Wait %d seconds' % (curr_scan, sleep_time))
                    elif scansInFile_list.index(str(curr_scan)) == (len(scansInFile_list) - 1):
                        scan = spec_data.getScan(curr_scan)
                        if len(scan.data) > 0:
                            curr_len = len(scan.data[scan.L[0]])
                        else:
                            curr_len = 0
                        logger.info('   Data points current in the scan #%d is %d'
                            % (curr_scan, curr_len))
                        if curr_len == 0:
                            pass
                        elif curr_len != last_len:
                            last_len = curr_len
                        else:
                            if _accu > 4:
                                break
                        sleep_time = 5 * _accu
                        logger.info('  Scan #%d may not be finished.  Wait %d seconds...'
                          % (curr_scan, sleep_time))
                    else:
                        logger.info('\t--------------------------------')
                        logger.info('  Scan #%d ready.\n' % curr_scan)
                        break
                    _accu += 1
                    scansInFile_list, spec_data = reindex_specfile(specfile_full)

                time.sleep(sleep_time)

            ds = Sector33SpecDataSource(projectDir, specName, specExt,
                                        instConfigName, detectorConfigName, roi=roi,
                                        pixelsToAverage=bin, scanList=scanRange,
                                        badPixelFile=badPixelFile,
                                        flatFieldFile=flatfieldFile,
                                        appConfig=appConfig)
            ds.setCurrentDetector(detectorName)
            ds.setProgressUpdater(_updateDataSourceProgress)
            ds.loadSource(mapHKL=mapHKL)

            fullRange = ds.getOverallRanges()
            if gridRange_input is None:
                gridRange = fullRange
            else:
                gridRange = checkGridRange(gridRange_input, fullRange)

            ds.setRangeBounds(gridRange)

            logger.info('  --------------------------------')

            gridMapper = QGridMapper(ds,
                                     outputFileName,
                                     outputType=BINARY_OUTPUT,
                                     nx=nx, ny=ny, nz=nz,
                                     transform=UnityTransform3D(),
                                     gridWriter=VTIGridWriter(),
                                     appConfig=appConfig)

            gridMapper.setProgressUpdater(_updateMapperProgress)
            gridMapper.doMap()

        with open('time.log', 'a') as time_log:
            endTime = datetime.datetime.now()
            time_log.write(f'End: {endTime}\n')
            time_log.write(f'Diff: {endTime - startTime}\n')

        logger.info('  --------------------------------')
    logger.info('=============================')
```

Note: `one_scan_time = config["maxTime_1Scan"]` from the original script is intentionally dropped — it was read but never used anywhere in the original either. `maxTime_1Scan` is still a required config key (existing sample JSON files provide it) even though nothing reads it, for forward-compatibility with `rsmconfig_v4.2_*.json` files already in the wild; `run()` simply doesn't need to look at it.

- [ ] **Step 4: Run the test to verify it passes**

```bash
pytest tests/workflows/test_angle_scan.py -v
```

Expected: `test_run_builds_datasource_and_mapper_from_config` passes.

- [ ] **Step 5: Delete the now-redundant standalone script**

```bash
git rm scripts/mapSpecAngleScan_v4.2.py
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Extract mapSpecAngleScan_v4.2.py into rsMap3D.workflows.angle_scan, wire as 'rsMap3D map-angle-scan'"
```

---

### Task 9: Extract `mapSpecParametricScan.py` into `rsMap3D.workflows.parametric_scan`

**Files:**
- Create (overwrite placeholder): `src/rsMap3D/workflows/parametric_scan.py`
- Delete: `scripts/mapSpecParametricScan.py`
- Test: `tests/workflows/test_parametric_scan.py`

**Interfaces:**
- Consumes: same `Sector33SpecDataSource` / `QGridMapper` constructors as Task 8.
- Produces: `rsMap3D.workflows.parametric_scan.run(config: dict) -> None`. `config` keys: `project_dir`, `config_dir`, `spec_file`, `scan_list` (list of scan-range strings), `use_HKL`, `detector_config`, `instrument_config`, `detector_name`, `binning`, `roi_setting` (or `None`, matching Task 8/10's convention), `nx`, `ny`, `nz`. This is a new schema (the original script took no config file at all — every value was a hand-edited module-level variable).

**Correction found during task review:** the code below originally dropped the ROI auto-detection fallback that the source script had (`dReader = detReader(detectorConfigName)`; `if roi is None: ... roi = [1, nPixels[0], 1, nPixels[1]]`), and dropped one diagnostic `print("imageToBeUsed %s" % imageToBeUsed)` line without converting it to `logger.info`. Both were restored to match Task 8's `angle_scan.py` handling of the identical `roi_setting` config key and the module docstring's claim of full print-to-logger coverage. The code block below reflects the corrected version.

**Known pre-existing bugs being fixed during this extraction (confirmed with the user before writing this task):**
1. `print scanRange[0]` is a Python 2 statement — hard `SyntaxError` under Python 3. Replaced with `logger.info` calls throughout (matching Task 8's style), since the whole script's only "console output" mechanism was `print`.
2. `tmpImageUsed = imageToBeUsed[scanRange[0]]` and `savImageUsed = imageToBeUsed[scanRange[0]]` were both references to the *same* list object, so "restoring" the image mask after each `doMap()` call was a no-op. Fixed with explicit `list(...)` copies.
3. The per-image loop ran `for imageInScan in range(1, len(imageToBeUsed[scanRange[0]])+1): tmpImageUsed[imageInScan] = False` — for a scan with N images, valid list indices are `0..N-1`, but the loop drove `imageInScan` up to `N` inclusive, guaranteeing an `IndexError` on the last (and, for a single-image scan, only) iteration. Fixed by looping 0-based over the mask while keeping 1-based numbering in filenames/log messages, matching the evident intent of the original `_N%d.vti` naming.

- [ ] **Step 1: Write the failing test**

Create `tests/workflows/test_parametric_scan.py`:
```python
'''
 Copyright (c) 2026, UChicago Argonne, LLC
 See LICENSE file.
'''
import importlib.resources
import os

import pytest

from rsMap3D.workflows import parametric_scan


class _FakeDataSource:
    instances = []

    def __init__(self, projectDir, projectName, projectExtension,
                 instConfigFile, detConfigFile, **kwargs):
        self.kwargs = kwargs
        self.imageToBeUsed = {1: [True, True, True]}
        _FakeDataSource.instances.append(self)

    def setCurrentDetector(self, name):
        self.currentDetector = name

    def setProgressUpdater(self, updater):
        pass

    def loadSource(self, mapHKL=False):
        pass

    def getOverallRanges(self):
        return (0, 1, 0, 1, 0, 1)

    def setRangeBounds(self, bounds):
        pass

    def getImageToBeUsed(self):
        return self.imageToBeUsed


class _FakeGridMapper:
    instances = []

    def __init__(self, dataSource, outputFileName, **kwargs):
        self.dataSource = dataSource
        self.outputFileName = outputFileName
        self.maskSnapshot = list(dataSource.imageToBeUsed[1])
        _FakeGridMapper.instances.append(self)

    def setProgressUpdater(self, updater):
        pass

    def doMap(self):
        pass


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeDataSource.instances.clear()
    _FakeGridMapper.instances.clear()
    yield


@pytest.fixture
def config():
    resources_dir = str(importlib.resources.files("rsMap3D") / "resources")
    return {
        "project_dir": "/tmp/does-not-need-to-exist",
        "config_dir": resources_dir,
        "spec_file": "CB_140303A_1.spec",
        "scan_list": ["1"],
        "use_HKL": False,
        "detector_config": "33bmDetectorGeometry.xml",
        "instrument_config": "33BM-instForXrayutilities.xml",
        "detector_name": "Pilatus",
        "binning": [1, 1],
        "roi_setting": [1, 487, 1, 195],
        "nx": 300, "ny": 300, "nz": 10,
    }


def test_run_masks_one_image_per_line_and_restores_mask(monkeypatch, config):
    monkeypatch.setattr(parametric_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(parametric_scan, "QGridMapper", _FakeGridMapper)

    parametric_scan.run(config)

    ds = _FakeDataSource.instances[0]
    # 3 fake images -> one grid map per image, 0-indexed internally
    assert len(_FakeGridMapper.instances) == 3
    for mapper in _FakeGridMapper.instances:
        # exactly one image is isolated (mask=True) per pass; the rest are excluded
        assert mapper.maskSnapshot.count(True) == 1
    # the mask must be restored to the original after every line runs
    assert ds.imageToBeUsed[1] == [True, True, True]


def test_run_names_output_files_1_indexed(monkeypatch, config):
    monkeypatch.setattr(parametric_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(parametric_scan, "QGridMapper", _FakeGridMapper)

    parametric_scan.run(config)

    names = sorted(m.outputFileName for m in _FakeGridMapper.instances)
    assert names == [
        os.path.join(config["project_dir"], "CB_140303A_1_N1.vti"),
        os.path.join(config["project_dir"], "CB_140303A_1_N2.vti"),
        os.path.join(config["project_dir"], "CB_140303A_1_N3.vti"),
    ]
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/workflows/test_parametric_scan.py -v
```

Expected: `NotImplementedError` from the placeholder `run()`.

- [ ] **Step 3: Write `src/rsMap3D/workflows/parametric_scan.py`**

```python
'''
 Copyright (c) 2017, UChicago Argonne, LLC
 See LICENSE file.

 Extracted from Scripts/mapSpecParametricScan.py so it can be driven from
 rsMap3D's CLI (`rsMap3D map-parametric-scan config.json`) instead of being
 run as a standalone, hand-edited script.

 The original script never ran successfully under any Python version:
   - It used Python 2 `print` statements (a SyntaxError under Python 3),
     replaced here with logger calls.
   - `tmpImageUsed` and `savImageUsed` were assigned from the same list
     object (`imageToBeUsed[scanRange[0]]`), so "restoring" the per-line
     image mask after doMap() was a no-op; fixed here with explicit
     copies.
   - The per-image loop ran `range(1, len(imageToBeUsed[...])+1)` and used
     the loop variable directly as a 0-based list index, guaranteeing an
     IndexError on its last (and, for a single-image scan, only)
     iteration; fixed here by looping 0-based over the mask while keeping
     1-based numbering in filenames/log messages, matching the evident
     intent of the original `_N%d.vti` naming.
'''
import logging
import os

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.datasource.DetectorGeometryForXrayutilitiesReader import \
    DetectorGeometryForXrayutilitiesReader as detReader
from rsMap3D.datasource.Sector33SpecDataSource import Sector33SpecDataSource
from rsMap3D.gui.rsm3dcommonstrings import BINARY_OUTPUT
from rsMap3D.mappers.gridmapper import QGridMapper
from rsMap3D.mappers.output.vtigridwriter import VTIGridWriter
from rsMap3D.transforms.unitytransform3d import UnityTransform3D
from rsMap3D.utils.srange import srange

logger = logging.getLogger(__name__)


def _updateDataSourceProgress(value1, value2):
    logger.info("DataSource Progress %s/%s" % (value1, value2))


def _updateMapperProgress(value1):
    logger.info("Mapper Progress %s" % (value1))


def run(config):
    '''
    Grid a parametric scan: each image within the scan represents a
    different sample-environment condition with all angles held constant,
    so one output file is produced per image in the scan.
    '''
    projectDir = config["project_dir"]
    configDir = config["config_dir"]
    specFile = config["spec_file"]
    scanList1 = config["scan_list"]
    mapHKL = config["use_HKL"]
    detectorConfigName = os.path.join(configDir, config["detector_config"])
    instConfigName = os.path.join(configDir, config["instrument_config"])
    detectorName = config["detector_name"]
    bin = config["binning"]
    roi = config["roi_setting"]
    nx = config["nx"]
    ny = config["ny"]
    nz = config["nz"]

    if not os.path.exists(detectorConfigName):
        raise Exception("Detector Config file does not exist: %s" %
                        detectorConfigName)
    if not os.path.exists(instConfigName):
        raise Exception("Instrument Config file does not exist: %s" %
                        instConfigName)

    dReader = detReader(detectorConfigName)

    if roi is None:
        detector = dReader.getDetectorById(detectorName)
        nPixels = dReader.getNpixels(detector)
        roi = [1, nPixels[0], 1, nPixels[1]]
    logger.info("ROI: %s " % roi)

    specName, specExt = os.path.splitext(specFile)
    appConfig = RSMap3DConfigParser()

    for scans in scanList1:
        scanRange = srange(scans).list()
        logger.info("scanRange %s" % scanRange)
        logger.info("specName, specExt: %s, %s" % (specName, specExt))
        ds = Sector33SpecDataSource(projectDir, specName, specExt,
                                    instConfigName, detectorConfigName, roi=roi,
                                    pixelsToAverage=bin, scanList=scanRange,
                                    appConfig=appConfig)
        ds.setCurrentDetector(detectorName)
        ds.setProgressUpdater(_updateDataSourceProgress)
        ds.loadSource(mapHKL=mapHKL)
        ds.setRangeBounds(ds.getOverallRanges())
        imageToBeUsed = ds.getImageToBeUsed()
        logger.info("imageToBeUsed %s" % imageToBeUsed)

        numImages = len(imageToBeUsed[scanRange[0]])
        for zeroBasedIndex in range(numImages):
            imageInScan = zeroBasedIndex + 1
            logger.info("Scan Line %d" % imageInScan)

            outputFileName = os.path.join(projectDir, specName +
                                          ('_N%d.vti' % imageInScan))
            gridWriter = VTIGridWriter()

            savedImageUsed = list(imageToBeUsed[scanRange[0]])
            tmpImageUsed = list(savedImageUsed)
            tmpImageUsed[zeroBasedIndex] = False
            ds.imageToBeUsed[scanRange[0]] = [not used for used in tmpImageUsed]

            gridMapper = QGridMapper(ds,
                                     outputFileName,
                                     outputType=BINARY_OUTPUT,
                                     transform=UnityTransform3D(),
                                     gridWriter=gridWriter,
                                     appConfig=appConfig,
                                     nx=nx, ny=ny, nz=nz)

            gridMapper.setProgressUpdater(_updateMapperProgress)
            gridMapper.doMap()
            ds.imageToBeUsed[scanRange[0]] = savedImageUsed
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/workflows/test_parametric_scan.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Delete the now-redundant standalone script**

```bash
git rm scripts/mapSpecParametricScan.py
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Extract mapSpecParametricScan.py into rsMap3D.workflows.parametric_scan, fixing its list-aliasing and off-by-one bugs, wire as 'rsMap3D map-parametric-scan'"
```

---

### Task 10: Extract `powderscan_RSM3D_2.1.py` into `rsMap3D.workflows.powder_scan`

**Files:**
- Create (overwrite placeholder): `src/rsMap3D/workflows/powder_scan.py`
- Delete: `scripts/powderscan_RSM3D_2.1.py`
- Test: `tests/workflows/test_powder_scan.py`

**Interfaces:**
- Consumes: `Sector33SpecDataSource` (as above), `rsMap3D.mappers.powderscanmapper.PowderScanMapper(dataSource, outputFileName, transform=..., gridWriter=..., appConfig=..., dataCoord=..., xCoordMin=..., xCoordMax=..., xCoordStep=..., plotResults=..., yScaling=..., writeXyeFile=...)`, `rsMap3D.mappers.output.powderscanwriter.PowderScanWriter()` — both pre-existing, unchanged.
- Produces: `rsMap3D.workflows.powder_scan.run(config: dict) -> None`. `config` keys: `project_dir`, `config_dir`, `instrument_config`, `detector_config`, `badpixel_file` (or `None`), `flat_field` (or `None`), `detector_name`, `binning`, `roi_setting` (or `None`), `data_coordinate`, `x_min`, `x_max`, `x_step`, `do_plot`, `plot_y`, `write_file`, `output_filename_fmt` (relative to `project_dir`, e.g. `"analysis_runtime/%s/%s_S%03d.xye"`), `datasets` (list of `{"spec_file": str, "scan_list": [...], "slices_not_used": [...]}`). This consolidates the original script's three parallel top-level lists (`specFileList`/`scanLists`/`slicesNotUsedLists`) into one per-dataset list, and is a new schema — the original script took no config file at all.

**Known pre-existing bug being fixed during this extraction:** the original did `if not os.path.exists(specName): os.makedirs(specName)` before writing output — this creates a directory named after the spec file *relative to the current working directory*, which is not where `PowderScanWriter.write()` actually opens its output file (`os.path.join(projectDir, "analysis_runtime", specName, ...)`, built from `output_filename_fmt`). `PowderScanWriter.write()` does a plain `open(outputFileName, "w")` with no directory creation of its own, so the original script would raise `FileNotFoundError` the first time it ran against a project directory without a pre-existing `analysis_runtime/<specName>/` folder. Fixed here by creating the actual output file's parent directory instead.

- [ ] **Step 1: Write the failing test**

Create `tests/workflows/test_powder_scan.py`:
```python
'''
 Copyright (c) 2026, UChicago Argonne, LLC
 See LICENSE file.
'''
import importlib.resources
import os

import pytest

from rsMap3D.workflows import powder_scan


class _FakeDataSource:
    instances = []

    def __init__(self, projectDir, projectName, projectExtension,
                 instConfigFile, detConfigFile, **kwargs):
        self.kwargs = kwargs
        self.imageToBeUsed = {1: [True, True, True]}
        _FakeDataSource.instances.append(self)

    def setCurrentDetector(self, name):
        self.currentDetector = name

    def setProgressUpdater(self, updater):
        pass

    def loadSource(self):
        pass

    def getOverallRanges(self):
        return (0, 1, 0, 1, 0, 1)

    def setRangeBounds(self, bounds):
        pass


class _FakePowderMapper:
    instances = []

    def __init__(self, dataSource, outputFileName, **kwargs):
        self.dataSource = dataSource
        self.outputFileName = outputFileName
        self.kwargs = kwargs
        _FakePowderMapper.instances.append(self)

    def setProgressUpdater(self, updater):
        pass

    def doMap(self):
        pass

    def getXCoordMin(self):
        return self.kwargs["xCoordMin"]

    def getXCoordMax(self):
        return self.kwargs["xCoordMax"]


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeDataSource.instances.clear()
    _FakePowderMapper.instances.clear()
    yield


@pytest.fixture
def config(tmp_path):
    resources_dir = str(importlib.resources.files("rsMap3D") / "resources")
    return {
        "project_dir": str(tmp_path),
        "config_dir": resources_dir,
        "instrument_config": "33BM-instForXrayutilities.xml",
        "detector_config": "33bmDetectorGeometry.xml",
        "badpixel_file": None,
        "flat_field": None,
        "detector_name": "Pilatus",
        "binning": [1, 1],
        "roi_setting": [1, 487, 1, 195],
        "data_coordinate": "tth",
        "x_min": 15, "x_max": 75, "x_step": 0.05,
        "do_plot": False,
        "plot_y": "Linear",
        "write_file": True,
        "output_filename_fmt": "analysis_runtime/%s/%s_S%03d.xye",
        "datasets": [
            {"spec_file": "CB_140303A_1.spec", "scan_list": ["1"], "slices_not_used": []},
        ],
    }


def test_run_builds_datasource_and_powdermapper_and_creates_output_dir(monkeypatch, tmp_path, config):
    monkeypatch.setattr(powder_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(powder_scan, "PowderScanMapper", _FakePowderMapper)

    powder_scan.run(config)

    assert len(_FakeDataSource.instances) == 1
    ds = _FakeDataSource.instances[0]
    assert ds.currentDetector == "Pilatus"
    assert ds.kwargs["roi"] == [1, 487, 1, 195]

    assert len(_FakePowderMapper.instances) == 1
    mapper = _FakePowderMapper.instances[0]
    assert mapper.kwargs["dataCoord"] == "tth"
    assert mapper.kwargs["xCoordMin"] == 15
    assert mapper.kwargs["xCoordMax"] == 75
    expected_output = os.path.join(
        str(tmp_path), "analysis_runtime", "CB_140303A_1", "CB_140303A_1_S001.xye")
    assert mapper.outputFileName == expected_output
    # the fix under test: the *actual* output directory must exist, not a
    # same-named directory relative to the current working directory.
    assert os.path.isdir(os.path.dirname(expected_output))
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/workflows/test_powder_scan.py -v
```

Expected: `NotImplementedError` from the placeholder `run()`.

- [ ] **Step 3: Write `src/rsMap3D/workflows/powder_scan.py`**

```python
'''
 Copyright (c) 2017, UChicago Argonne, LLC
 See LICENSE file.

 Extracted from Scripts/powderscan_RSM3D_2.1.py so it can be driven from
 rsMap3D's CLI (`rsMap3D powder-scan config.json`) instead of being run as
 a standalone, hand-edited script. Originally written by Christian
 Schleputz, modified by Zhan Zhang, APS, ANL.

 Fix note: the original created `os.makedirs(specName)` (relative to the
 current working directory) before writing output, but PowderScanWriter
 actually opens its file at `project_dir/analysis_runtime/<specName>/...`
 (built from output_filename_fmt) and does not create any directories
 itself -- the original would raise FileNotFoundError the first time it
 ran against a project directory that didn't already happen to have that
 nested folder. This extraction creates the real output file's parent
 directory instead.
'''
import logging
import os
import time
from itertools import zip_longest

import numpy as np

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.datasource.DetectorGeometryForXrayutilitiesReader import \
    DetectorGeometryForXrayutilitiesReader as detReader
from rsMap3D.datasource.Sector33SpecDataSource import Sector33SpecDataSource
from rsMap3D.mappers.output.powderscanwriter import PowderScanWriter
from rsMap3D.mappers.powderscanmapper import PowderScanMapper
from rsMap3D.transforms.unitytransform3d import UnityTransform3D
from rsMap3D.utils.srange import srange

logger = logging.getLogger(__name__)


def _updateDataSourceProgress(value1, value2):
    logger.info("\t\tDataLoading Progress %.3f%%/%s%%" % (value1, value2))


def _updateMapperProgress(value1):
    logger.info("\t\tMapper Progress -- Current Curve %.3f%%" % (value1))


def _normalizeScanList(scan_list):
    if not isinstance(scan_list, list):
        if isinstance(scan_list, (int, float)):
            scan_list = [int(scan_list)]
        elif isinstance(scan_list, str):
            scan_list = srange(scan_list).list()
        elif isinstance(scan_list, range):
            scan_list = list(scan_list)
    return scan_list


def run(config):
    '''
    Reduce one or more spec scans per dataset into 1D powder-diffraction
    curves (.xye files), one curve per scan (or per combined scan-range).
    '''
    projectDir = config["project_dir"]
    configDir = config["config_dir"]
    detectorName = config["detector_name"]
    bin = config["binning"]
    roi = config["roi_setting"]
    data_coordinate = config["data_coordinate"]
    x_min_0 = config["x_min"]
    x_max_0 = config["x_max"]
    x_step = config["x_step"]
    do_plot = config["do_plot"]
    plot_y = config["plot_y"]
    write_file = config["write_file"]
    output_filename_fmt = os.path.join(projectDir, config["output_filename_fmt"])

    instConfigName = os.path.join(configDir, config["instrument_config"])
    detectorConfigName = os.path.join(configDir, config["detector_config"])
    badPixelFile = config["badpixel_file"]
    if badPixelFile is not None:
        badPixelFile = os.path.join(configDir, badPixelFile)
    flatfieldFile = config["flat_field"]
    if flatfieldFile is not None:
        flatfieldFile = os.path.join(configDir, flatfieldFile)

    if not os.path.exists(detectorConfigName):
        raise Exception("Detector Config file does not exist: %s" %
                        detectorConfigName)
    if not os.path.exists(instConfigName):
        raise Exception("Instrument Config file does not exist: %s" %
                        instConfigName)
    if badPixelFile is not None and not os.path.exists(badPixelFile):
        raise Exception("Bad Pixel file does not exist: %s" %
                        badPixelFile)
    if flatfieldFile is not None and not os.path.exists(flatfieldFile):
        raise Exception("Flat field file does not exist: %s" %
                        flatfieldFile)

    dReader = detReader(detectorConfigName)
    if roi is None:
        detector = dReader.getDetectorById(detectorName)
        nPixels = dReader.getNpixels(detector)
        roi = [1, nPixels[0], 1, nPixels[1]]
    logger.info('  ROI: %s ' % roi)

    datasets = config["datasets"]
    specFileList = [dataset["spec_file"] for dataset in datasets]
    scanLists = [dataset["scan_list"] for dataset in datasets]
    slicesNotUsedLists = [dataset.get("slices_not_used", []) for dataset in datasets]

    for (specfile, scan_list, slicesNotUsed_list) in zip_longest(
            specFileList, scanLists, slicesNotUsedLists):

        specName, specExt = os.path.splitext(specfile)
        logger.info('=============================')
        logger.info('  Starting SPEC file : %s' % (specfile))
        logger.info('    Scans            : %s' % (scan_list))

        scan_list = _normalizeScanList(scan_list)

        slicesNotUsed_scanN = []
        slicesNotUsed_sliceN = []
        for slicesNotUsed_oneset in slicesNotUsed_list:
            scan_num = srange(slicesNotUsed_oneset[0]).list()
            slice_nums = srange(slicesNotUsed_oneset[1]).list()
            if slice_nums:
                slicesNotUsed_scanN.extend(scan_num)
                slicesNotUsed_sliceN.append(slice_nums * len(scan_num))

        num_curves = len(scan_list)
        progress = 0
        for scans in scan_list:
            logger.info('  --------------------------------')
            logger.info('      Reading scans # %s' % (str(scans)))

            scans = _normalizeScanList(scans)
            fileNameMarker = scans[0]

            outputFileName = output_filename_fmt % (specName, specName, fileNameMarker)
            os.makedirs(os.path.dirname(outputFileName), exist_ok=True)

            x_min = x_min_0
            x_max = x_max_0

            _start_time = time.time()

            appConfig = RSMap3DConfigParser()
            ds = Sector33SpecDataSource(projectDir, specName, specExt,
                    instConfigName, detectorConfigName, roi=roi, pixelsToAverage=bin,
                    scanList=scans, badPixelFile=badPixelFile,
                    flatFieldFile=flatfieldFile, appConfig=appConfig)
            ds.setCurrentDetector(detectorName)
            ds.setProgressUpdater(_updateDataSourceProgress)
            ds.loadSource()
            ds.setRangeBounds(ds.getOverallRanges())
            logger.info('  --------------------------------')

            for onescan in scans:
                if onescan in slicesNotUsed_scanN:
                    myindex = slicesNotUsed_scanN.index(onescan)
                    slice_list = slicesNotUsed_sliceN[myindex]
                    logger.info('      Points #%s in scan #%s ignored.  ' %
                            (str(slice_list), str(onescan)))
                    my_len = len(ds.imageToBeUsed[onescan])
                    for slice_ in slice_list:
                        if slice_ in range(-my_len, my_len):
                            ds.imageToBeUsed[onescan][slice_] = False
                else:
                    logger.info('       No slice removed. ')
            logger.info('  --------------------------------')

            powderMapper = PowderScanMapper(ds,
                     outputFileName,
                     transform=UnityTransform3D(),
                     gridWriter=PowderScanWriter(),
                     appConfig=appConfig,
                     dataCoord=data_coordinate,
                     xCoordMin=x_min,
                     xCoordMax=x_max,
                     xCoordStep=x_step,
                     plotResults=do_plot,
                     yScaling=plot_y,
                     writeXyeFile=write_file)

            powderMapper.setProgressUpdater(_updateMapperProgress)
            powderMapper.doMap()

            x_min_output = powderMapper.getXCoordMin()
            x_max_output = powderMapper.getXCoordMax()
            nbins = np.round((x_max_output - x_min_output) / x_step)
            logger.info('  \t %s minimum : %.3f' % (data_coordinate, x_min_output))
            logger.info('  \t %s maximum : %.3f' % (data_coordinate, x_max_output))
            logger.info('  \t %s stepsize: %.3f' % (data_coordinate, x_step))
            logger.info('  \t %s nbins   : %.3f' % (data_coordinate, nbins))

            progress += 100.0 / num_curves
            logger.info('  Elapsed time for current curve: %.3f seconds' % (time.time() - _start_time))
            logger.info('  Mapper Progress -- Current File : %.1f%%' % (progress))
            if write_file:
                logger.info('  Output filename : %s' % (outputFileName))
            else:
                logger.info('  Output file %s disabled. ' % (outputFileName))
        logger.info('  --------------------------------')
    logger.info('=============================')
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
pytest tests/workflows/test_powder_scan.py -v
```

Expected: passes.

- [ ] **Step 5: Delete the now-redundant standalone script**

```bash
git rm scripts/powderscan_RSM3D_2.1.py
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Extract powderscan_RSM3D_2.1.py into rsMap3D.workflows.powder_scan, fixing its output-directory bug, wire as 'rsMap3D powder-scan'"
```

---

### Task 11: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Fresh editable install from a clean checkout state**

```bash
pip uninstall -y rsMap3D
pip install -e ".[dev,xpcs]"
```

Expected: succeeds with no errors (confirms `pyproject.toml` metadata, package discovery under `src/`, and package-data glob are all correct).

- [ ] **Step 2: Confirm the package still imports and reports the same version**

```bash
python -c "import rsMap3D; print(rsMap3D.__version__)"
```

Expected: `1.3.1`.

- [ ] **Step 3: Confirm the console script and all four subcommands are registered**

```bash
rsMap3D --help
rsMap3D map-angle-scan --help
rsMap3D map-parametric-scan --help
rsMap3D powder-scan --help
```

Expected: each prints argparse help with no import errors.

- [ ] **Step 4: Run the full test suite**

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v
```

Expected: no collection errors; the new `test_cli.py` and `tests/workflows/*` tests all pass. Some pre-existing tests may still fail for reasons unrelated to this restructure (e.g. tests that were already logically broken before this migration, beyond the specific Python 2/3.12-alias fixes made in Task 6) — note any such failures for a follow-up, but they must not block this plan: the acceptance bar for this plan is "every test file collects and imports cleanly, and no test that used to pass now fails because of the restructure."

- [ ] **Step 5: Confirm no stray references to old paths remain**

```bash
grep -rn "rsMap3D/test\b\|rsMap3D/resources/spec\|rsMap3D/docs\b" src/ tests/ scripts/ docs/ pyproject.toml 2>/dev/null
```

Expected: no output.

- [ ] **Step 6: Confirm the final top-level tree matches the target layout**

```bash
ls
```

Expected: `.gitignore`, `LICENSE`, `README.md`, `pyproject.toml`, `src/`, `tests/`, `scripts/`, `docs/` — no `setup.py`, `MANIFEST.in`, `Scripts/`, `.project`, `.pydevproject`, `examples/` (anglecalcexamples/ stays inside `src/rsMap3D/`, see Task 4's note).

- [ ] **Step 7: Final commit (if Step 1's reinstall or any cleanup produced changes)**

```bash
git status --short
git add -A
git commit -m "Final verification pass for src-layout restructure" --allow-empty
```
