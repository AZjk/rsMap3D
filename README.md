# rsMap3D

> Map x-ray scattering images into 3D reciprocal space maps

rsMap3D transforms raw x-ray diffraction images collected during synchrotron beamline experiments into **reciprocal space maps (RSMs)** using [xrayutilities](https://pypi.org/project/xrayutilities/) for the Q-space calculations. It runs as a **PySide6 desktop application** or as **headless CLI workflows** driven by JSON configs.

## Quick start

```bash
# GUI mode (default)
rsMap3D

# Headless workflows
rsMap3D map-angle-scan config.json
rsMap3D map-parametric-scan config.json
rsMap3D powder-scan config.json
```

## Installation

rsMap3D requires **Python 3.9+** and **PySide6** with **VTK 8.2+**.

```bash
# Clone the repository
git clone https://github.com/AZjk/rsMap3D.git
cd rsMap3D

# Create and activate a conda environment
conda create -n rsmap3d python=3.13 -y
conda activate rsmap3d

# Install PySide6 and VTK (conda handles VTK binaries)
conda install -c conda-forge pyside6 vtk -y

# Install the package in editable mode
pip install -e .

# Optional: XPCS support (adds pyepics)
pip install -e ".[xpcs]"

# Optional: dev tools (pytest, ruff)
pip install -e ".[dev]"
```

### Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | Qt GUI framework |
| vtk | 3D visualization (VTK render windows in the GUI) |
| numpy | Numerical arrays |
| xrayutilities | Q-space gridder, stereographic projections |
| h5py + hdf5plugin | HDF5/NeXus file I/O |
| matplotlib | Powder diffraction plots |
| spec2nexus | SPEC file indexing |
| pillow | TIFF image reading |
| pyepics (optional) | EPICS PV polling for realtime scans |

### Optional / Manual

- **pyimm** — required only for the `XPCSSpecDataSource` (IMM/XPCS format). Not on PyPI; obtain from the beamline infrastructure.
- **ParaView** — required for `scripts/paraview/` plotting scripts, which use `pvpython` (ParaView's bundled Python interpreter), not the conda env.

## Supported data formats

rsMap3D provides beamline-specific data sources for spec files, HDF5/NeXus, and IMM formats.

| Source | Format | Beamline / Facility |
|--------|--------|---------------------|
| `Sector33SpecDataSource` | SPEC + TIFF images | APS Sector 33-ID |
| `Sector12SpecDataSource` | SPEC + TIFF images | APS Sector 12-BM |
| `Sector28SpecDataSource` | SPEC + HDF5 images | APS CHEX 28-ID |
| `Sector34NexusEscanSource` | HDF5/NeXus escan | APS Sector 34 |
| `NSLSIISector4SpecDataSource` | SPEC + HDF5 images | NSLS-II 4-ID-E |
| `Sector12NSLSIISpecDataSource` | SPEC + TIFF images | NSLS-II Sector 12 |
| `S1HighEnergyDiffractionDS` | .par param + binary frames | APS 1-BM |
| `s8waxpcsSpecDataSource` | SPEC + HDF5 (XPCS) | APS 8-ID-E |
| `s28waxpcsSpecDataSource` | SPEC + HDF5 (XPCS) | APS CHEX 28-ID |
| `XPCSSpecDataSource` | SPEC + IMM files | APS XPCS beamlines |

Each data source reads **instrument geometry** and **detector geometry** from XML config files (sample/detector circles, primary beam direction, pixel size, distance, etc.).

## Architecture

### Core pipeline

```
DataSource ──→ Mapper ──→ GridWriter
  (load raw     (grid Q-space   (write
   data)         using            output)
                  xrayutilities)
```

1. **DataSource** (`rsMap3D/datasource/`) loads raw scan data, extracts angles, intensities, and Q-space geometry.
2. **Mapper** (`rsMap3D/mappers/`) drives `xrayutilities` to compute Q coordinates (qx, qy, qz) and bin intensities into a regular 3D grid.
3. **GridWriter** (`rsMap3D/mappers/output/`) serializes the result to disk.

### Class hierarchy

```
AbstractDataSource
  └── AbstractXrayutilitiesDataSource
        └── SpecXMLDrivenDataSource
              ├── Sector33SpecDataSource
              ├── Sector12SpecDataSource
              ├── Sector28SpecDataSource
              ├── NSLSIISector4SpecDataSource
              ├── Sector12NSLSIISpecDataSource
              ├── s8waxpcsSpecDataSource
              ├── s28waxpcsSpecDataSource
              └── XPCSSpecDataSource
        └── S1HighEnergyDiffractionDS
  └── Sector34NexusEscanSource

AbstractGridMapper
  ├── QGridMapper        (3D reciprocal space)
  ├── PowderScanMapper   (1D powder diffraction)
  └── XPCSGridLocationMapper

AbstractGridWriter
  ├── VTIGridWriter
  ├── ImageStackWriter
  └── XPCSGridLocationWriter
```

### GUI

The PySide6 application (`rsMap3D/rsmEdit.py`) provides a tabbed workflow:

1. **File** — select a data source format and configure input paths (spec file, image directory, instrument/detector XML configs, bad-pixel and flat-field files).
2. **Data Range** — set Q-space bounding boxes (qx, qy, qz min/max).
3. **Scans** — preview the scan extent in a VTK 3D view.
4. **Process Data** — choose an output format and run the mapper.

## CLI subcommands

### `rsMap3D gui`

Launch the desktop application (default when no subcommand is given).

### `rsMap3D map-angle-scan CONFIG.json`

Grid spec angle-scan data into one or more VTI reciprocal space maps.

**Example config** (`scripts/rsmconfig_v4.2_lsfo_IntegerPeaks.json`):

```json
{
    "project_dir": "/path/to/data/",
    "detector_config": "detector_geometry.xml",
    "instrument_config": "instrument_geometry.xml",
    "badpixel_file": "badpixels.txt",
    "flat_field": null,
    "use_HKL": true,
    "detector_name": "Eiger500k",
    "binning": [1, 1],
    "roi_setting": [10, 1020, 10, 504],
    "nx": 400,
    "ny": 400,
    "nz": 200,
    "grid_range": null,
    "datasets": [
        {
            "spec_file": "LSFO_001_Cryo.spec",
            "scan_list": [["316-318"]],
            "scan_range": {
                "cycles": 1,
                "scans_per_cycle": 30,
                "rsm_sets": [{"start": 117, "end": 207}]
            }
        }
    ]
}
```

### `rsMap3D map-parametric-scan CONFIG.json`

Grid a parametric scan, producing **one VTI output per image** (e.g., one map per temperature point).

### `rsMap3D powder-scan CONFIG.json`

Reduce multiple scans into **1D powder-diffraction curves** (.xye files).

## Output formats

| Format | Extension | Description | Viewer |
|--------|-----------|-------------|--------|
| VTI | `.vti` | VTK XML Image Data (3D volume, binary or ASCII) | [ParaView](https://www.paraview.org/) |
| Image stack | `.tif` | TIFF slices along one axis (x, y, or z) | Any image viewer |
| Powder scan | `.xye` | Three-column text (x, intensity, error) with metadata headers | Origin, matplotlib |
| XPCS grid locations | `.csv` | Q-space grid coordinates (qx, qy, qz) | Any spreadsheet |

## Instrument / detector configuration

Sample and detector geometry is specified in **XML config files** read by:

- `InstForXrayutilitiesReader` — instrument config (sample/detector circles, primary beam direction, monitors, filters, sample angle mapping functions)
- `DetectorGeometryForXrayutilitiesReader` — detector config (pixel size, dimensions, distance, center channel pixel, pixel directions)

Example configs are shipped as package data in `src/rsMap3D/resources/` and as test fixtures in `tests/fixtures/`.

## Configuration

User settings are stored in **`~/.rsMap3D.ini`**:

```ini
[Memory]
maxImageMemory = 104857600   ; 100 MB — controls how scans are split into memory-limited passes

[InputForms]
InputForm0 = rsMap3D.gui.input.s33specscanfileform.S33SpecScanFileForm
; ... auto-discovered form classes ...

[MPI]
mpi_host_file =
mpi_worker_count = 1
```

Available input forms are auto-discovered from `rsMap3D.gui.input` at runtime.

## Project structure

```
rsMap3D/
├── pyproject.toml              # Build config, dependencies, entry point
├── src/rsMap3D/
│   ├── cli.py                  # CLI entry point (gui, map-angle-scan, ...)
│   ├── rsmEdit.py              # PySide6 GUI main window
│   ├── config/                 # Config parsing, logging
│   ├── datasource/             # Beamline-specific data sources
│   │   ├── abstractDataSource.py
│   │   ├── Sector33SpecDataSource.py
│   │   └── ...
│   ├── gui/
│   │   ├── input/              # Input forms (one per beamline format)
│   │   └── output/             # Output forms (VTI, image stack, powder, XPCS)
│   ├── mappers/
│   │   ├── gridmapper.py       # 3D Q-space gridder
│   │   ├── powderscanmapper.py # 1D powder diffraction
│   │   └── output/             # Grid writers (VTI, TIFF, CSV, .xye)
│   ├── transforms/             # 3D transforms (unity, pole map)
│   ├── utils/                  # Scan range parser
│   └── workflows/              # CLI headless workflows
├── tests/                      # pytest test suite
│   └── fixtures/               # Test data (spec, HDF5, XML configs)
├── scripts/                    # Legacy reference scripts, sample configs
└── docs/                       # Sphinx documentation
```

## License

Copyright (c) 2012–2026, UChicago Argonne, LLC. All Rights Reserved. See [LICENSE](LICENSE).

## Credits

rsMap3D is developed by researchers at the [Advanced Photon Source](https://www.aps.anl.gov/), Argonne National Laboratory, and collaborators at NSLS-II.