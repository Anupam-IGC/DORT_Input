# DORT R-Z Input Preparation API

A lightweight Python API for preparing **DORT two-dimensional R-Z transport inputs**.

The project provides tools for constructing and validating R-Z mesh/material models,
visualizing the resulting geometry, generating DORT/FIDO geometry-material arrays,
and calculating angular quadrature sets.

> **Project status:** under active development. The API currently prepares important
> parts of a DORT input, but it does not yet generate a complete problem deck.

## Features

- Piecewise-uniform and explicit **R/Z meshes**
- Named **materials** and rectangular R-Z **regions**
- Priority-based filling for nested/overlapping structures
- Validation of mesh, material references, overlaps, and unfilled cells
- Material and region plots for model verification
- DORT/FIDO geometry-material arrays:
  - `2*` — Z mesh boundaries
  - `4*` — R mesh boundaries
  - `8$` — material-zone map
  - `9$` — zone-to-material mapping
  - optional identity `84$` edit-region mapping
- Angular quadrature generation:
  - legacy DORT/DOQDP-compatible S_N construction
  - positive-weight product quadrature for higher angular resolution
  - validation of directions, weights, ordering, and angular moments
  - direct generation of DORT `81*`, `82*`, and `83*` arrays

## Requirements

Python 3.10+ is recommended.

```bash
pip install -r requirements.txt
```

Run scripts from the repository root, or ensure the repository root is on
`PYTHONPATH`.

## Quick Start

### R-Z geometry and material filling

```python
from model import DORTModel
from writer import DORTWriter

model = DORTModel("simple_shield")

for material in ("Sodium", "Core", "SS316"):
    model.add_material(material)

model.mesh.r.add_segment(0.0, 100.0, step=5.0)
model.mesh.r.add_segment(100.0, 140.0, step=2.0)
model.mesh.z.add_segment(-50.0, 50.0, step=5.0)

model.set_background("Sodium")

model.add_region(
    "core",
    material="Core",
    r=(0.0, 100.0),
    z=(-50.0, 50.0),
    priority=20,
)

model.add_region(
    "shield",
    material="SS316",
    r=(100.0, 140.0),
    z=(-50.0, 50.0),
    priority=30,
)

model.build()

writer = DORTWriter(model)
writer.write_block4_fragment("geometry_material_fragment.inp")
```

### Angular quadrature

```python
from quadrature import generate_legacy_quadrature

quad = generate_legacy_quadrature(
    order=8,
    symmetry="half",
)

print(quad.summary_text())
quad.write_dort("quadrature.inc")
```

For higher angular resolution:

```python
from quadrature import generate_product_quadrature

quad = generate_product_quadrature(
    polar_order=24,
    azimuthal_order=32,
)
```

The quadrature module can directly generate:

```text
81*  directional weights
82*  radial direction cosines
83*  axial direction cosines
```

## Main Modules

| Module | Purpose |
|---|---|
| `mesh.py` | R and Z mesh construction |
| `materials.py` | Material registry |
| `regions.py` | R-Z region definitions |
| `model.py` | Model assembly, validation, and final maps |
| `plotting.py` | Material and region visualization |
| `writer.py` | DORT/FIDO geometry-material output |
| `quadrature.py` | DORT angular quadrature generation and validation |

## Documentation

Detailed usage, examples, API references, DORT array mapping, and development
notes are maintained in the Sphinx/Read-the-Docs documentation:

- [Documentation source](docs/source/index.rst)
- [DORT mapping notes](docs/DORT_MAPPING.md)

Build locally with:

```bash
pip install -r docs/requirements.txt
cd docs
make html
```

On Windows:

```bat
cd docs
make.bat html
```

Then open `docs/build/html/index.html`.

## Recommended Workflow

```text
define mesh/materials/regions
        ↓
build and validate model
        ↓
inspect material/region plots
        ↓
generate/select quadrature
        ↓
validate quadrature
        ↓
generate DORT input fragments
        ↓
verify against the complete DORT deck
```

For production calculations, perform appropriate spatial, angular, and
scattering-order convergence checks.

## Current Scope

The project currently focuses on **R-Z geometry/material preparation and angular
quadrature generation**. Full automatic DORT-deck generation, source definition,
cross-section mixing, execution, and output parsing remain future development
areas.

## License

No license is currently included. Add an appropriate `LICENSE` file before
broad public distribution.
