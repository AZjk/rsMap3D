# Drop IMM format support

## Context

rsMap3D's `XPCSSpecDataSource` and `XPCSSpecScanFileForm` depend on `pyimm`, an internal
beamline package that is **not on PyPI** and must be obtained from the beamline infrastructure.
This creates three problems:

1. **Clean installs are impossible.** Anyone who `pip install -e .` without manually obtaining
   `pyimm` gets an import error whenever the XPCS data source or GUI form is loaded — even if
   they never intend to use IMM data. The import is guarded by a try/except, but the failure
   surface is opaque (the form disappears from the auto-discovered input form list with no
   explanation).
2. **`pyimm` is no longer maintained.** The package has not been updated since the original XPCS
   beamline infrastructure was decommissioned. No active user base depends on it.
3. **The only remaining XPCS functionality — grid location output — does not need `pyimm`.**
   `XPCSGridLocationMapper` and `XPCSGridLocationWriter` are generic: they take `qx, qy, qz`
   arrays from *any* `AbstractXrayutilitiesDataSource` and write CSV output. They do not import
   `pyimm` and have no IMM-specific logic.

This spec removes the IMM dependency while preserving the XPCS grid location pipeline.

## Decisions

1. **Delete `xpcsspecdatasource.py` and `xpcsspecscanfileform.py`.** These are the only files
   that import `pyimm`. They provide the complete IMM data source stack (data loading, image
   reading, dark-field correction, scan parsing) and the GUI form that configures them. Both are
   dead code if `pyimm` is unavailable.
2. **Keep `XPCSGridLocationMapper` and `XPCSGridLocationWriter`.** These have zero `pyimm`
   imports. They are generic CSV writers for Q-space grid locations and can be driven by any
   data source that supports `rawmapSingle()`. Removing them provides no benefit and loses a
   working feature.
3. **Keep the `[xpcs]` optional dependency (`pyepics`).** The `pyepics` dependency is used by
   the `angle_scan` workflow for EPICS PV polling in realtime scan polling — it is not related
   to `pyimm`. The name `xpcs` is a historical artifact; renaming it is out of scope.
4. **No deprecation period.** Since `pyimm` is not pip-installable and has no active user base,
   a gradual deprecation cycle adds cost with no benefit. This is a clean removal.

## Scope

### Files to delete (2)

| File | Lines | Reason |
|------|-------|--------|
| `src/rsMap3D/datasource/xpcsspecdatasource.py` | ~520 | Main IMM data source, all `pyimm` imports |
| `src/rsMap3D/gui/input/xpcsspecscanfileform.py` | ~180 | GUI input form for XPCS/IMM |

### Files to modify (5)

1. **`src/rsMap3D/gui/input/__init__.py`** — Remove the (already-commented-out) XPCS import
   line. The file currently contains only commented imports; this one gets deleted.
2. **`src/rsMap3D/gui/input/s1highenergydiffractionform.py:353`** — Remove one warning message
   that says `"The IMM file entered is invalid"`. The S1 high-energy diffraction form uses this
   message in a dialog that validates file paths. The wording is misleading for the S1 context
   (which uses `.par` files, not `.imm`); it should say something format-agnostic like
   `"The entered file path is invalid"`.
3. **`README.md`** — Remove:
   - `pyimm` mention in optional dependencies
   - `XPCSSpecDataSource` row in data format table
   - "IMM" from the supported format description
4. **`CLAUDE.md`** — Remove IMM references from the architecture overview:
   - Data source format list (spec, HDF5, XPCS/**IMM** → spec, HDF5)
   - Dependency note about `pyimm`
5. **`docs/superpowers/specs/2026-07-15-standard-src-layout-design.md`** — Remove `pyimm`
   references from the spec document (decisions 10, 12, and the Risks section).

### Files explicitly NOT touched

| File | Reason |
|------|--------|
| `mappers/xpcsgridlocationmapper.py` | Generic CSV writer, no `pyimm` import |
| `mappers/output/xpcsgridlocationwriter.py` | Generic CSV writer, no `pyimm` import |
| `gui/output/processxpcsgridlocationform.py` | GUI output form, no `pyimm` import — stays as valid XPCS grid location output option |
| `pyproject.toml` | `pyepics` stays; no `pyimm` declared anywhere |
| `scripts/paraview/*.py` | ParaView scripts, unrelated |

## Verification

1. **`ruff check . && ruff format --check .`** — Clean after removal (no dangling imports).
2. **`QT_QPA_PLATFORM=offscreen pytest tests/`** — All existing tests pass (no tests reference
   XPCS/IMM code; the `__init__.py` import was already commented out).
3. **Import smoke test** — `python -c "from rsMap3D.datasource import *" ` succeeds without
   importing `pyimm`.
4. **GUI auto-discovery** — `RSMap3DConfigParser.buildDefaultConfig()` does not include
   `XPCSSpecScanFileForm` in the discovered input forms list.

## Risks

- **Low.** The two deleted files are the only `pyimm` consumers. The XPCS grid location
  mapper/writer are independent and will continue to work with any
  `AbstractXrayutilitiesDataSource`. No test code references the deleted modules.
- If any external beamline scripts reference `XPCSSpecDataSource` by dotted path (the same
  concern raised for `anglecalcexamples` in the src-layout migration), those scripts will
  `ImportError` after this change. A `grep` of the repo and `scripts/` confirms no such
  references exist internally. External references would need to be identified with the
  beamline ops team before deploying.