# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

rsMap3D is a PyQt5 desktop application (from the Advanced Photon Source, Argonne National Lab) that
transforms images collected during an x-ray scattering experiment into a 3D reciprocal space map,
using `xrayutilities` for the underlying Q-space calculations. It supports several beamline-specific
data formats (spec files + area-detector images, HDF5/NeXus, XPCS/IMM), and can output VTI volumes,
TIFF image stacks, or CSV data.

The package root is `rsMap3D/` (note: repo root and package share the name). Entry points live in
`Scripts/` (`Scripts/rsMap3D`, `Scripts/rsMap3D.bat`) which just call `rsMap3D.rsmEdit`.

## Running the application

Use the `d2607_rsmap3d` conda environment (`/home/beams/MQICHU/miniforge3/envs/d2607_rsmap3d`, Python
3.13), which has PyQt5/VTK/xrayutilities etc. already installed:

```bash
conda activate d2607_rsmap3d
python -m rsMap3D.rsmEdit      # or: python Scripts/rsMap3D
```

or without activating:

```bash
/home/beams/MQICHU/miniforge3/envs/d2607_rsmap3d/bin/python -m rsMap3D.rsmEdit
```

This launches the PyQt5 GUI (`MainDialog` in `rsMap3D/rsmEdit.py`), a tabbed workflow: File → Data
Range → Scans → Process Data.

## Dependencies

Not fully captured in `setup.py` (which only lists `spec2nexus` and `pillow`) — in practice the code
also depends on `PyQt5`, `vtk`, `numpy`, `xrayutilities`, `h5py`/`hdf5plugin` (NeXus/HDF5 sources),
`matplotlib`, and optionally `pyimm`/`epics` for XPCS/IMM beamlines and `paraview` for the plotting
scripts under `Scripts/`. There is no `requirements.txt` or pinned lock file; check imports in the
relevant `datasource`/`gui` module before assuming a dependency is available.

Python 3 / PyQt5 / VTK 8.2+ is required (the codebase was ported from Python 2 / PyQt4 around v1.2.0).
Some files under `rsMap3D/test/` still contain Python 2 syntax (e.g. `print` statements without
parentheses) and are stale/non-runnable as-is — don't assume everything in `test/` currently passes.

## Tests

Tests use `unittest` (not pytest), live under `rsMap3D/test/`, and mirror the package layout
(`test/config`, `test/datasource`, `test/gui`). Many rely on fixture files under
`rsMap3D/resources/` (spec files, XML instrument/detector configs, "problem files" for negative
tests) via relative paths computed from `__file__`, so they must be run with that relative layout
intact. Run an individual test module directly, e.g.:

```bash
conda run -n d2607_rsmap3d python -m unittest rsMap3D.test.config.testrsmap3dconfig
```

Some tests are known-broken (Python 2 leftovers, GUI tests requiring a display); verify a specific
test file works before trusting it rather than assuming the whole suite is green.

## Architecture

### Data flow

1. A **DataSource** (`rsMap3D/datasource/`) knows how to load a beamline's raw scan format (spec
   file + images, HDF5/NeXus, IMM) and turn it into arrays of angles/intensities plus Q-space
   geometry (sample/detector circles, UB matrix, wavelength, ROI, bad-pixel/flat-field corrections).
2. A **Mapper** (`rsMap3D/mappers/`) drives `xrayutilities` to grid the raw angle/intensity data from
   a DataSource into a regular 3D Q-space grid (`gridmapper.py`), a powder/1D profile
   (`powderscanmapper.py`), or XPCS grid locations.
3. A **GridWriter** (`rsMap3D/mappers/output/`) serializes the gridded result — VTI, a TIFF image
   stack, ASCII, powder CSV, or XPCS location CSV.
4. The **GUI** (`rsMap3D/gui/`) wires input forms (`gui/input/`) to the DataSource classes and output
   forms (`gui/output/`) to the Mapper/GridWriter classes, coordinated by `rsmEdit.MainDialog`.

### Class hierarchies (extend these, don't special-case around them)

- `AbstractDataSource` (`datasource/abstractDataSource.py`) → `AbstractXrayutilitiesDataSource`
  (`datasource/AbstractXrayUtilitiesDataSource.py`) → beamline-specific sources such as
  `Sector33SpecDataSource`, `Sector12SpecDataSource`, `Sector28SpecDataSource`,
  `NSLSIISector4SpecDataSource`, `sector34nexusescansource.Sector34NexusEscanSource`,
  `s1highenergydiffractionds`, `xpcsspecdatasource`. Several sector-specific spec sources share
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

`RSMap3DConfigParser` (`rsMap3D/config/rsmap3dconfigparser.py`) builds its default config by
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

### Instrument/detector configuration

Sample/detector geometry (circle directions, primary beam direction, pixel size, distance to
detector, etc.) is read from XML files via `InstForXrayutilitiesReader.py` and
`DetectorGeometryForXrayutilitiesReader.py` in `rsMap3D/datasource/`. `datasource/DetectorGeometry/`
holds the base/per-technique detector geometry classes (`DetectorGeometryBase`,
`DetectorGeometryForEScan`). Example XML configs live in `rsMap3D/resources/` (per-sector
subdirectories like `33-id-e/`) and `rsMap3D/resources/config/`.

### Logging and errors

Logging is centralized through `rsMap3D/config/rsmap3dlogging.py` (`LOGGER_NAME`, `LOGGER_DEFAULT`
dict config, `METHOD_ENTER_STR`/`METHOD_EXIT_STR` conventions used throughout for debug tracing).
`rsmEdit.py` looks for `~/rsMap3DLog.config` and falls back to the built-in dict config. All custom
exceptions derive from `RSMap3DException` (`rsMap3D/exception/rsmap3dexception.py`).

### Standalone scripts

`Scripts/` also contains older/parallel command-line scripts (`mapSpecAngleScan*.py`,
`mapSpecParametricScan.py`, `powderscan_RSM3D_2.1.py`) and ParaView plotting helpers
(`paraviewPlot.py`, `paraviewPlot_tile.py`) that use the same DataSource/Mapper classes outside the
GUI — useful references for scripting batch/headless processing.
