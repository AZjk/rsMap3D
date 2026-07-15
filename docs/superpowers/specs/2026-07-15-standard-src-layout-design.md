# Restructure rsMap3D to a standard src-layout

## Context

rsMap3D currently ships as a flat, pre-PEP 621 layout: `setup.py` +
`MANIFEST.in`, an importable package (`rsMap3D/`) that also contains its own
`test/`, `docs/`, `resources/` (mixing shipped config examples with 36MB of
test fixtures), and `anglecalcexamples/`. A separate `Scripts/` directory
holds the installed GUI launcher plus several standalone, hand-edited
analysis scripts and ParaView plotting scripts. Some Eclipse/PyDev metadata
(`.project`, `.pydevproject`, referencing Python 2.7) is still checked in,
and two Python-2-era `.pyc` files are committed to git.

The goal is to convert this to the standard modern layout:

```
my-project/
├── .gitignore
├── README.md
├── pyproject.toml
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── main.py
│       └── utils.py
└── tests/
    ├── __init__.py
    └── test_main.py
```

This is a pure repackaging/layout change: no algorithm, mapper, datasource,
or GUI behavior changes.

## Decisions

These were confirmed interactively before writing this spec:

1. **Package name stays `rsMap3D`.** No rename to `rsmap3d`. Every
   `from rsMap3D.x import y` import, and any beamline-side config or script
   referencing `rsMap3D.*` dotted paths, keeps working unchanged. Only the
   physical location moves from `rsMap3D/` to `src/rsMap3D/`.
2. **GUI launcher becomes a `console_scripts` entry point.**
   `rsmEdit.py`'s `if __name__ == "__main__":` body becomes a `main()`
   function; `pyproject.toml` declares
   `[project.scripts] rsMap3D = "rsMap3D.cli:main"`. The old
   `Scripts/rsMap3D` / `Scripts/rsMap3D.bat` wrapper scripts are dropped.
3. **`Scripts/` utilities move to a lowercase `scripts/` folder and the
   actively-maintained ones become CLI subcommands**, wired through a new
   `rsMap3D.cli` module with `argparse` subparsers:
   - `mapSpecAngleScan_v4.2.py` → `rsMap3D map-angle-scan`
   - `mapSpecParametricScan.py` → `rsMap3D map-parametric-scan`
   - `powderscan_RSM3D_2.1.py` → `rsMap3D powder-scan`
   - No subcommand (or `rsMap3D gui`) launches the existing GUI.
   - The superseded `mapSpecAngleScan.py` and `mapSpecAngleScan_v2.py` move
     into `scripts/` unmodified, as historical reference only — not wired
     into the CLI, not refactored.
   - Sample JSON configs (`rsmconfig_v4.2_*.json`) move alongside them.
4. **ParaView scripts (`paraviewPlot.py`, `paraviewPlot_tile.py`) move to
   `scripts/paraview/` unmodified and stay outside the CLI.** They only run
   under ParaView's bundled `pvpython` interpreter (`from paraview.simple
   import *`), which is a different Python environment than the
   `d2607_rsmap3d` conda env used for everything else, so wiring them into
   `rsMap3D`'s argparse CLI would produce a subcommand that only works in a
   different interpreter than the one that installed it.
5. **`resources/` splits by purpose:**
   - Shipped package data (the `*.xml` instrument/detector config examples)
     move to `src/rsMap3D/resources/`, declared via
     `[tool.setuptools.package-data]`.
   - Test-only fixtures (spec files, images, "problem files for testing",
     the test config dir) move to `tests/fixtures/`, used only by the test
     suite, not installed with the package.
6. **Tests move to `tests/` and adopt pytest naming/runner:**
   - Directory structure under `tests/` mirrors the current structure under
     `rsMap3D/test/` (`config/`, `datasource/`, `datasource/detectorgeometry/`,
     `datasource/sector1/`, `gui/input/`, `gui/output/`).
   - Every test file is renamed to match pytest's default `test_*.py`
     discovery pattern (e.g. `testrsmap3dconfig.py` →
     `test_rsmap3dconfig.py`, `testScanForm.py` → `test_scan_form.py`).
     Test code stays `unittest.TestCase`-based — pytest runs those natively,
     so no test logic is rewritten.
   - Known-broken Python 2 syntax (bare `print` statements without
     parentheses) in `testsector33specdatasource.py`,
     `testdetectorgeometryforxrayutilitiesreader.py`, and
     `testsector34nexusescan.py`, is fixed so the files at least import and
     collect cleanly. No other test behavior changes.
   - Fixture path constants (currently `THIS_DIR`-relative paths into
     `../../resources/...`) are rewritten to point at the new
     `tests/fixtures/...` location.
   - The two git-tracked, Python-2-era `.pyc` files
     (`test/datasource/detectorgeometry/__init__.pyc` and
     `testdetectorgeometryforescan.pyc`) are deleted, not moved.
   - `pytest` is added as a `dev` optional-dependency; a
     `[tool.pytest.ini_options]` table sets `testpaths = ["tests"]`.
7. **Build backend: `setuptools`**, declared via PEP 621 `[project]` +
   `[tool.setuptools]` tables in `pyproject.toml`. `setup.py` and
   `MANIFEST.in` are removed. No new build tool introduced.
8. **`docs/` moves to a top-level `docs/` folder**, out of the importable
   package (Sphinx source, install/tutorial PDFs, icons). The committed
   `docs/build/` (8MB of generated HTML/doctrees) is removed from git and
   added to `.gitignore` — it's regenerable via `make html` and shouldn't be
   tracked.
9. **`anglecalcexamples/` moves to a top-level `examples/` folder**
   (`examples/anglecalcexamples/`). Nothing in `src/rsMap3D` imports this
   subpackage today — it exists purely as copy-and-adapt reference code for
   a user's `<sampleAngleMapFunction>` PYTHONPATH plugin, referenced by path
   in instrument XML configs, not as a Python import path.
10. **Dependency list in `pyproject.toml` is corrected** to match actual
    imports, instead of carrying forward `setup.py`'s incomplete
    `install_requires = [spec2nexus, pillow]`:
    - Core: `PyQt5`, `vtk`, `numpy`, `xrayutilities`, `h5py`, `hdf5plugin`,
      `matplotlib`, `spec2nexus`, `pillow`.
    - `[project.optional-dependencies] xpcs = ["pyepics"]` for the
      NSLS-II/XPCS-only data sources (`pyimm` is not on PyPI and stays a
      documented manual install, not a declared dependency).
11. **Eclipse/PyDev metadata (`.project`, `.pydevproject`) is deleted** —
    stale, references a Python 2.7 interpreter, not used by any tooling
    once the project is driven by `pyproject.toml`.
12. `README` is renamed `README.md` (content — mostly a version history log
    — kept as-is, reformatted with Markdown headers).

## Target layout

```
rsMap3D/
├── .gitignore
├── README.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── rsMap3D/
│       ├── __init__.py
│       ├── rsmEdit.py            # gains a main() function
│       ├── cli.py                # NEW: argparse entry point + subcommands
│       ├── constants.py
│       ├── config/
│       ├── datasource/
│       ├── exception/
│       ├── gui/
│       ├── mappers/
│       ├── transforms/
│       ├── utils/
│       └── resources/            # only the shipped *.xml package_data
├── tests/
│   ├── config/
│   ├── datasource/
│   │   ├── detectorgeometry/
│   │   └── sector1/
│   ├── gui/
│   │   ├── input/
│   │   └── output/
│   └── fixtures/                 # moved from rsMap3D/resources/
├── scripts/
│   ├── mapSpecAngleScan.py       # kept verbatim, reference only
│   ├── mapSpecAngleScan_v2.py    # kept verbatim, reference only
│   ├── rsmconfig_v4.2_lsfo_IntegerPeaks.json
│   ├── rsmconfig_v4.2_lsfo_IntegerPeaks_batch.json
│   └── paraview/
│       ├── paraviewPlot.py
│       └── paraviewPlot_tile.py
├── examples/
│   └── anglecalcexamples/
│       ├── copycolumn.py
│       └── sumgammamu.py
└── docs/
    ├── conf.py, index.rst, Makefile, make.bat
    ├── Icons/, Installation/, Tutorial/
    └── (docs/build/ dropped from git, added to .gitignore)
```

## `pyproject.toml` sketch

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
    {name = "John Hammonds"}, {name = "Christian Schleputz"},
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
dev  = ["pytest"]

[project.scripts]
rsMap3D = "rsMap3D.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
rsMap3D = ["resources/*.xml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Version can alternatively be read dynamically from
`src/rsMap3D/__init__.py.__version__` via `[tool.setuptools.dynamic]` — an
implementation-time choice, not a design fork.

## CLI design

```
rsMap3D                                 # no subcommand → launches the GUI (today's default)
rsMap3D gui                             # explicit alias for the same thing
rsMap3D map-angle-scan CONFIG.json      # wraps mapSpecAngleScan_v4.2's logic
rsMap3D map-parametric-scan ...         # wraps mapSpecParametricScan.py, parameterized
rsMap3D powder-scan ...                 # wraps powderscan_RSM3D_2.1.py, parameterized
```

`src/rsMap3D/cli.py` uses `argparse` with subparsers. Each subcommand calls
a function extracted from the corresponding script's current top-level code
(the extraction targets are the actively-maintained scripts only — see
decision 3). `rsmEdit.py`'s `if __name__ == "__main__":` block becomes
`def main():`; the CLI's no-subcommand path calls it.

## Out of scope

- No behavior/algorithm changes to any mapper, datasource, or GUI form.
- `mapSpecAngleScan.py` / `_v2.py` are relocated only, not refactored into
  the CLI.
- `paraviewPlot.py` / `paraviewPlot_tile.py` are relocated only, remain
  standalone scripts requiring `pvpython`.
- Fixing GUI tests that need a real display (e.g. via `xvfb`) is not part
  of this pass — carried forward as today's existing limitation.
- No dependency version pinning/upper-bounding beyond what's already
  implied by "PyQt5 + VTK 8.2+" in the current docs.
- No CI/workflow setup (e.g. GitHub Actions) is added as part of this
  restructure unless requested separately.

## Risks

- Extracting `map-angle-scan` / `map-parametric-scan` / `powder-scan` logic
  out of hand-edited "User parameters" scripts into parameterized functions
  is the highest-risk step — it's the one place behavior could
  inadvertently change. The implementation plan should specify each
  script's current parameter set precisely and verify identical output on
  a known fixture before/after.
- `pyimm` and ParaView are not pip-installable; anything that imports them
  can only be smoke-tested where those are already available.
