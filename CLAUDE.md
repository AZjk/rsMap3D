# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

rsMap3D is a PySide6 desktop application (from the Advanced Photon Source, Argonne National Lab) that
transforms images collected during an x-ray scattering experiment into a 3D reciprocal space map,
using `xrayutilities` for the underlying Q-space calculations. It supports several beamline-specific
data formats (spec files + area-detector images, HDF5/NeXus), and can output VTI volumes,
TIFF image stacks, or CSV data.

The repo uses a standard `src/` layout: the importable package lives at `src/rsMap3D/` (import path
stays `rsMap3D`, e.g. `from rsMap3D.datasource.Sector33SpecDataSource import Sector33SpecDataSource`).
Packaging is `pyproject.toml` (setuptools backend) — there is no `setup.py`.

## Running the application

Use the `d2607_rsmap3d` conda environment (`/home/beams/MQICHU/miniforge3/envs/d2607_rsmap3d`, Python
3.13), which has PySide6/VTK/xrayutilities etc. already installed:

```bash
conda activate d2607_rsmap3d
pip install -e .        # editable install, once per env
rsMap3D                 # launches the GUI (equivalent to `rsMap3D gui`)
```

or without activating: `/home/beams/MQICHU/miniforge3/envs/d2607_rsmap3d/bin/rsMap3D`.

This launches the PySide6 GUI (`MainDialog` in `src/rsMap3D/rsmEdit.py`), a tabbed workflow: File → Data
Range → Scans → Process Data.

### CLI subcommands

`src/rsMap3D/cli.py` (argparse) also exposes three headless workflow subcommands, each taking a JSON
config file path — these replace what used to be standalone, hand-edited scripts under `Scripts/`:

```bash
rsMap3D map-angle-scan CONFIG.json        # Sector 33 spec angle-scan -> reciprocal space map
rsMap3D map-parametric-scan CONFIG.json   # Sector 33 parametric scan -> one map per image
rsMap3D powder-scan CONFIG.json           # Sector 33 spec scans -> 1D powder-diffraction curves
```

Each subcommand's config schema and logic lives in `src/rsMap3D/workflows/{angle_scan,parametric_scan,
powder_scan}.py`, each exposing a `run(config: dict) -> None`. `scripts/rsmconfig_v4.2_*.json` are
sample configs for `map-angle-scan`. `rsMap3D --help` / `rsMap3D <subcommand> --help` for usage.

## Dependencies

Declared in `pyproject.toml`: `PySide6`, `vtk`, `numpy`, `xrayutilities`, `h5py`, `hdf5plugin`,
`matplotlib`, `spec2nexus`, `pillow`. Optional extras: `pip install -e ".[xpcs]"` adds `pyepics`
(needed by the XPCS/NSLS-II-specific data sources and the angle-scan workflow's realtime-scan-polling
feature); `pip install -e ".[dev]"` adds `pytest`. ParaView
`paraview` (used by `scripts/paraview/*.py`) are not on PyPI and remain manual installs — check imports
in the relevant `datasource`/`scripts` module before assuming either is available.

Python 3.9+ / PySide6 / VTK 8.2+ is required (the codebase was ported from Python 2 / PyQt4 to
Python 3 / PyQt5 around v1.2.0, then from PyQt5 to PySide6 — PySide6 is the Qt Company's own,
LGPL-licensed binding, vs. PyQt5's GPL/commercial dual license from Riverbank Computing).

## Tests

Tests use `pytest` (unittest.TestCase-style test code, pytest as the runner/discovery), live under
top-level `tests/`, and mirror the package layout (`tests/config`, `tests/datasource`, `tests/gui`).
Fixture data lives under `tests/fixtures/` (spec files, XML instrument/detector configs, "problem
files" for negative tests, a legacy `.rsMap3D` config) — resolved via relative paths computed from
`__file__`, so run pytest from anywhere but don't move test files independently of their fixtures.
A handful of package-data XML configs (root-level `*.xml` under `src/rsMap3D/resources/`) are shipped
with the installed package rather than living in `tests/fixtures/`; tests that need them locate them
via `importlib.resources.files('rsMap3D') / 'resources' / '<name>.xml'`.

```bash
pip install -e ".[dev]"
pytest tests/                                    # full suite
pytest tests/config/test_rsmap3dconfig.py -v     # single file
QT_QPA_PLATFORM=offscreen pytest tests/ -v       # headless (no real display for GUI tests)
```

As of the last restructure, the suite is 86 passed / 14 failed — the 14 failures are pre-existing
Python-2→3 production bugs unrelated to test infrastructure (e.g. a `str`/bytes mismatch in
`InstForXrayutilitiesReader.py`), not newly broken tests. Verify a specific test file's current state
before trusting it rather than assuming a clean pass.

## Architecture

### Data flow

1. A **DataSource** (`src/rsMap3D/datasource/`) knows how to load a beamline's raw scan format (spec
   file + images, HDF5/NeXus) and turn it into arrays of angles/intensities plus Q-space
   geometry (sample/detector circles, UB matrix, wavelength, ROI, bad-pixel/flat-field corrections).
2. A **Mapper** (`src/rsMap3D/mappers/`) drives `xrayutilities` to grid the raw angle/intensity data
   from a DataSource into a regular 3D Q-space grid (`gridmapper.py`), a powder/1D profile
   (`powderscanmapper.py`), or XPCS grid locations.
3. A **GridWriter** (`src/rsMap3D/mappers/output/`) serializes the gridded result — VTI, a TIFF image
   stack, ASCII, powder CSV, or XPCS location CSV.
4. The **GUI** (`src/rsMap3D/gui/`) wires input forms (`gui/input/`) to the DataSource classes and
   output forms (`gui/output/`) to the Mapper/GridWriter classes, coordinated by `rsmEdit.MainDialog`.
   The **CLI** (`src/rsMap3D/cli.py` + `src/rsMap3D/workflows/`) wires the same DataSource/Mapper
   classes together headlessly, driven by a JSON config instead of the GUI forms.

### Class hierarchies (extend these, don't special-case around them)

- `AbstractDataSource` (`datasource/abstractDataSource.py`) → `AbstractXrayutilitiesDataSource`
  (`datasource/AbstractXrayUtilitiesDataSource.py`) → beamline-specific sources such as
  `Sector33SpecDataSource`, `Sector12SpecDataSource`, `Sector28SpecDataSource`,
  `NSLSIISector4SpecDataSource`, `sector34nexusescansource.Sector34NexusEscanSource`,
  `s1highenergydiffractionds`. Several sector-specific spec sources share
  common logic via `specxmldrivendatasource.SpecXMLDrivenDataSource`.
- `AbstractGridMapper` (`mappers/abstractmapper.py`) → `gridmapper.QGridMapper`,
  `powderscanmapper.PowderScanMapper`, `xpcsgridlocationmapper`.
- `AbstractFileView` (`gui/input/abstractfileview.py`, a `QDialog`) → per-beamline input forms in
  `gui/input/` (e.g. `s33specscanfileform.py`, `s12specscanfileform.py`, `s34hdfescanfileform.py`).
  Mixins `usesxmlinstconfig.py` / `usesxmldetectorconfig.py` add XML instrument/detector config
  loading to a form.
- `AbstractOutputView` (`gui/output/abstractoutputview.py`, a `QDialog`) → output forms in
  `gui/output/` (VTI, image stack, powder scan, XPCS grid location), each paired with a GridWriter.

### Plugin discovery

`RSMap3DConfigParser` (`src/rsMap3D/config/rsmap3dconfigparser.py`) builds its default config by
introspecting the `rsMap3D.gui.input` module for `AbstractFileView` subclasses
(`findFormClasses`) and recording them by fully-qualified class name in the user's `rsMap3D.ini`
(`~/rsMap3D.ini` by default). This is how the "File" tab's list of supported input formats is
populated — adding a new beamline input form to `gui/input/` and making it importable from
`rsMap3D.gui.input` is enough for it to be picked up. `RSMap3DConfig`
(`config/rsmap3dconfig.py`) is the older, superseded XML-based config format; `rsmap3dconfigparser`
falls back to reading old XML config to seed the new INI-based config's `MaxImageMemory`.

Per-beamline angle-mapping logic can also be supplied externally: a Python module placed on
`PYTHONPATH` and referenced by name (with package path) can provide the angle-mapping function used
by `Sector33SpecDataSource`-style sources, rather than editing the data source class itself.
`src/rsMap3D/anglecalcexamples/` ships two example modules (`copycolumn.py`, `sumgammamu.py`)
demonstrating this — it stays inside the installed package (not moved to a top-level `examples/`)
specifically because instrument XML configs reference it by its installed dotted path, e.g.
`module="rsMap3D.anglecalcexamples.sumgammamu"` (see `tests/fixtures/33-id-e/33IDE_sixc.xml`).

### Instrument/detector configuration

Sample/detector geometry (circle directions, primary beam direction, pixel size, distance to
detector, etc.) is read from XML files via `InstForXrayutilitiesReader.py` and
`DetectorGeometryForXrayutilitiesReader.py` in `src/rsMap3D/datasource/`.
`datasource/DetectorGeometry/` holds the base/per-technique detector geometry classes
(`DetectorGeometryBase`, `DetectorGeometryForEScan`). A handful of example/test XML configs ship as
package data at `src/rsMap3D/resources/*.xml`; the larger set of per-sector example configs and test
fixtures (`33-id-e/`, `34-id-escan/`, etc.) live under `tests/fixtures/`.

### Logging and errors

Logging is centralized through `src/rsMap3D/config/rsmap3dlogging.py` (`LOGGER_NAME`, `LOGGER_DEFAULT`
dict config, `METHOD_ENTER_STR`/`METHOD_EXIT_STR` conventions used throughout for debug tracing).
`rsmEdit.py` looks for `~/rsMap3DLog.config` and falls back to the built-in dict config. The CLI
workflow modules share a separate console-logging setup (`src/rsMap3D/workflows/_common.py`) so
`map-angle-scan`/`map-parametric-scan`/`powder-scan` all print progress to stdout. All custom
exceptions derive from `RSMap3DException` (`src/rsMap3D/exception/rsmap3dexception.py`).

### Standalone scripts

`scripts/` holds older/superseded reference scripts not wired into the CLI: `mapSpecAngleScan.py` /
`mapSpecAngleScan_v2.py` (superseded by the `map-angle-scan` subcommand), `powderscan_newRSM3D.py` /
`powderscan_win.py` (superseded by `powder-scan`), and `scripts/paraview/paraviewPlot.py` /
`paraviewPlot_tile.py` (ParaView plotting helpers — these require ParaView's own bundled Python
interpreter, `pvpython`, not the `d2607_rsmap3d` conda env, so they're intentionally not part of the
`rsMap3D` CLI).
