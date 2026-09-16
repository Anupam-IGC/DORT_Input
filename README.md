# DORT R-Z Input Preparation API

A Python toolkit for preparing **R-Z inputs for a locally modified DORT workflow**.
The package focuses on model-driven input preparation: define the physical model
and calculation intent in readable Python, then let the API generate the
corresponding DORT/FIDO fragments.

## What it covers

- piecewise R/Z mesh construction and region filling;
- natural-number material registration and overlap/priority checks;
- external `mix.inp -> mixf.cr` macroscopic mixture workflow;
- automatic local negative `9$$` references (`-1, -7, -13, ...` for P5);
- material/region plots and zone inspection;
- legacy and product angular quadrature (`81*`, `82*`, `83*`);
- readable first-eigenvalue, rerun, and fixed-source run controls;
- unit-20/unit-21 eigenvalue restart workflow;
- fixed-source `96**` fields selected from materials, regions, zones, or R-Z mesh;
- file-based `98**` group spectra.

> **Local convention:** macroscopic mixing is performed by the external
> `m_ia_oa.for` program. `mixf.cr` is then read by modified DORT on the
> configured `NTSIG` unit (51 in the verified sample). The API does not replace
> this with stock DORT `10$$/11$$/12*` in-core mixing.

## Quick start

The recommended mixture workflow is spreadsheet-driven.  A workbook contains
``Nuclide`` and ``MAT No.`` columns followed by one column per final mixture.

```python
from model import DORTModel
from writer import DORTWriter

model = DORTModel("demo")
model.prepare_mixtures_from_excel(
    "mixtures.xlsx",
    sheet_name="Read",
    legendre_order=5,
    output_dir="mixture_output",
)

# Workbook column names are now normal model materials.
model.mesh.r.add_segment(0.0, 100.0, step=5.0)
model.mesh.z.add_segment(-50.0, 50.0, step=5.0)
model.set_background("Sodium")
model.add_region(
    "steel_region",
    material="Carbon Steel",
    r=(60.0, 100.0),
    z=(-30.0, 30.0),
    priority=20,
)
model.build()

writer = DORTWriter(model, cross_section_unit=51)
writer.write_block4_fragment("geometry_material.inc")
```

The spreadsheet import writes ``mix.inp``, ``Mixture_Names.txt``, and the
compact ``dort_mix_cards.txt`` used by the established external-mixer workflow.
Programmatic ``model.add_mixture(...)`` definitions remain available.

## Documentation

The Sphinx documentation is organized into a short **Start** section, a nested
**User Guide**, comprehensive **Examples**, and an autodoc **API Reference**.

Build locally with:

```bash
cd docs
make clean
make html
```

Behind a proxy or on an offline machine:

```bash
DORT_DOCS_OFFLINE=1 make html
```

Then open `docs/build/html/index.html`.

## Comprehensive examples

Run from the repository root:

```bash
python examples/comprehensive_mixture_spreadsheet.py
python examples/comprehensive_geometry.py
python examples/comprehensive_eigenvalue_first.py
python examples/comprehensive_eigenvalue_rerun.py
python examples/comprehensive_fixed_source.py
python examples/comprehensive_quadrature.py
```

Generated files are written under `example_output/`.

## Main modules

| Module | Purpose |
|---|---|
| `model.py` | high-level physical model |
| `mesh.py`, `regions.py` | R-Z geometry |
| `materials.py`, `mixtures.py` | materials, Excel mixture import, and external cross-section recipes |
| `writer.py` | DORT geometry/material fragments |
| `run_control.py` | readable calculation modes and control settings |
| `source.py` | fixed-source spatial field and group spectrum |
| `quadrature.py` | angular quadrature generation |
| `plotting.py`, `quadrature_plotting.py` | visual inspection |

Spreadsheet import requires `pandas` and `openpyxl`; both are included in `requirements.txt`.

The project is under active development; it deliberately generates validated
fragments rather than claiming full coverage of every locally modified DORT
input card.
