# DORT R-Z Input Preparation

`dort-input` prepares R-Z DORT inputs and reads the resulting VARFLM
`dortflux.bin` output. It covers mixture bookkeeping, piecewise meshes,
material regions, quadrature, run controls, flux and dose post-processing,
plots, and consistency checks for the locally modified DORT workflow.

The package does **not** invent a complete universal deck. Generated fragments
are intended to be inserted into a trusted local DORT template after review.

## Start in five minutes

Python 3.10 or newer is required. Install the wheel:

```bash
python -m pip install dort_input-0.4.1-py3-none-any.whl
```

Or, from the extracted source directory:

```bash
python -m pip install .
python examples/modeling_basics.py
```

The first tutorial writes its results to
`example_output/01_modeling_basics/`. Review these outputs before changing the
model:

- `materials.png` — final material assigned to every mesh cell;
- `regions.png` — region that won each overlap;
- `material_region_union.png` — material fill with every region interface and a material label per connected area;
- `geometry_outlines.csv` — material, region, and combined XY outline series for Origin or Excel;
- `geometry_material.inc` — DORT `2**`, `4**`, `8$$`, and `9$$` arrays;
- `mixtures/` — `mix.inp` and material/table mapping aids.

The writer defaults to one DORT zone per used material. A model with 29 used
mixtures therefore has 29 `9$$` values and `IZM=29` in `62$$`; the `8$$` cell
map uses those same zone numbers. Select `zone_policy="region"` explicitly only
when repeated references for distinct physical regions are intended.

## Recommended modeling sequence

1. Load a reviewed mixture workbook or define mixtures programmatically.
2. Put R and Z mesh boundaries at important physical interfaces.
3. Fill the domain with a background material and named regions.
4. Use priorities only for intentional overlaps.
5. Build with strict bounds and inspect counts, individual cells, and plots.
6. Review the DORT zone and cross-section table mappings.
7. Add a validated quadrature and one run profile.
8. Check required/forbidden optional cards.
9. Write the combined input with a reviewed `1**` group array and compare it
   with a known working case.

## Progressive examples

Run these from the repository root, in order:

| Example | Focus |
|---|---|
| `modeling_basics.py` | Mixtures, piecewise mesh, regions, priorities, inspection, plots, and geometry writing |
| `eigenvalue_input.py` | Complete first eigenvalue deck and optional-card policy |
| `fixed_source_input.py` | Region/material/mesh source selection, a group spectrum, and `96**`/`98**` output |
| `eigenvalue_restart.py` | Unit-21 output to unit-20 restart-file workflow |
| `quadrature_comparison.py` | Validating and plotting legacy and product quadratures |
| `process_dort_output.py` | Inspecting VARFLM, streaming groupwise dose, plotting, and saving arrays |

```bash
python examples/modeling_basics.py
python examples/eigenvalue_input.py
python examples/fixed_source_input.py
python examples/eigenvalue_restart.py
python examples/quadrature_comparison.py
python examples/process_dort_output.py run_01/dortflux.bin --neutron-factors NeutronDose.txt --photon-factors GammaDose.txt
```

The supplied materials and spectra are teaching data, not benchmark models.
Replace them with reviewed project data before using an input physically.

## Process a DORT flux file

The reader obtains I/J mesh sizes, group counts, neutron/photon split,
I-set assignments, and mesh boundaries from the VARFLM header. A response
calculation streams the file one group at a time:

```python
from dort_input import DortFluxReader, load_group_factors

reader = DortFluxReader("run_01/dortflux.bin")
meta = reader.metadata
print(meta.shape)  # (group, axial, radial), e.g. (217, 650, 181)

nf = load_group_factors("NeutronDose.txt", meta.neutron_groups)
gf = load_group_factors("GammaDose.txt", meta.photon_groups)
dose = reader.dose_rate(nf, gf, scale=3600.0)
fig, ax = reader.plot_field(dose.total, label="Dose rate", log=True)
fig.savefig("dose_rate.png", dpi=180, bbox_inches="tight")
reader.write_rz_csv(dose.total, "dose_total_rz.csv")
```

Conversion factors and flux normalization must be consistent. `scale=3600`
converts a rate per second into a rate per hour only when the factors are
specified per unit fluence. The reader does not infer physical units.
`read_scalar_flux()` loads the full cube if you need per-group fluxes;
`read_scalar_flux(groups=[0, 1])` loads selected **zero-based** groups.
The cube is ordered `[group, axial, radial]`. Missing cells in a variable
I mesh are represented by `NaN`. See `docs/source/output_processing.rst`.
The CSV has `R,Z,Value` columns at active cell centres; it omits padded
radial cells and keeps the mesh's coordinate units. You can also call
`reader.write_rz_csv(reader.read_scalar_flux(groups=[0])[0], "group_1_rz.csv")`.

## Geometry plots

Use `r_extent` and `z_extent` to zoom either plot. The material plot can
show only material interfaces, with one material ID centered in each visible,
connected material area (including separate islands of the same material):

```python
from dort_input.plotting import (
    save_material_plot, save_material_region_union_plot, save_region_plot,
    write_outline_csv,
)

save_material_plot(
    model, "material_detail.png",
    r_extent=(35.0, 85.0), z_extent=(-30.0, 30.0),
    show_material_boundaries=True, show_material_ids=True,
)
save_region_plot(
    model, "region_detail.png",
    r_extent=(35.0, 85.0), z_extent=(-30.0, 30.0),
)
save_material_plot(
    model, "material_outline.png",
    r_extent=(35.0, 85.0), z_extent=(-30.0, 30.0),
    color_fill=False,
)
save_material_region_union_plot(model, "material_region_union.png")
write_outline_csv(model, "geometry_outlines.csv")
```

The displayed boundaries follow the **built material ID map** at mesh edges,
including the effect of priorities. Use `show_mesh=True` to display every
fine-mesh cell edge, or the existing `show_ids=True` to label every cell.
The outline option enables one ID per connected material area and material
boundaries automatically. ID plots use a wider figure with automatic aspect;
pass `aspect="equal"` to retain the physical R-Z proportions or `figsize=(14, 9)`
to give a crowded model more room. Material legends show **ID: name** pairs
when IDs are plotted, include only materials visible in the requested extents,
and use multiple columns below the plot when needed.

The combined plot draws a boundary whenever the final material **or** region
changes. Adjacent regions sharing a material stay separate and receive that
material's name inside each connected area. The outline CSV contains
`Material_R,Material_Z`, `Region_R,Region_Z`, and `Union_R,Union_Z` column pairs.
Plot each pair as its own XY line series in Origin or Excel. Two endpoint rows
and one blank separator row represent each line segment; blank rows prevent
unrelated segments from being joined. Coordinates follow the model mesh units.

Background cells have base priority `0` in `cell_assignment()`; an unfilled
cell, when explicitly allowed, reports `None`. If the same material occurs in
multiple axial intervals, describe the intervals as a list of pairs instead
of a dictionary, because duplicate dictionary keys discard earlier intervals.

## What is generated

| Fragment or file | Purpose |
|---|---|
| `mix.inp`, `Mixture_Names.txt` | External macroscopic-mixer input and audit mapping |
| `2**`, `4**`, `8$$`, `9$$` | R-Z mesh, zone map, and local cross-section references |
| `81**`, `82**`, `83**` | Angular quadrature |
| `61$$`, `62$$`, `63**` | File units and run controls |
| `93**`, `94**`, `95**` | Uniform initial flux for a first eigenvalue run |
| `96**`, `98**` | Mesh-based fixed-source spatial field and energy spectrum |

Macroscopic mixing remains external. The established `m_ia_oa.for` workflow
converts `mix.inp` to `mixf.cr`, which modified DORT reads from `NTSIG`
(normally unit 51). Neither the mixer, DORT executable, nor nuclear-data
library is bundled.

A first eigenvalue input includes `93**`, `94**`, and `95**` starting-flux
cards filled with `1.0` by default (`93** F 1.0 t`, etc.). Each follows the
geometry block and terminates separately. The restart profile omits them.

Write the full input after supplying the problem-specific group-wise `1**`
array. You may pass `IGM` numbers or an already formatted `1**` card with FIDO
operators. The accepted local card order is:

```text
title
61$$, 62$$, 63**
t
t
82**, 83**, 81**, 84$$ ... t
1**, 2**, 4**, 8$$, 9$$ ... t
93** ... t, 94** ... t, 95** ... t  (when INPFXM=3)
t
```

```python
writer.write_complete_input(
    "dortinp_first.inp", run_control=run, quadrature=quadrature,
    array1=group_values, title="My case",
)
```

The combined writer checks `MM`, `IZM`, `IM`, `JM`, `ISCTM`, `NTSIG`, the
quadrature, and required optional cards. Supply physically reviewed `1**`
values and confirm the selected run profile against your local solver.

The angular arrays have exactly `MM` entries each and no per-array terminator.
The `84$$` card closes their block with `t`. The `9$$` card closes the later
group/geometry block with `t`.

## Mixture command

Spreadsheet preparation is also available from the command line:

```bash
dort-mixture mixtures.xlsx --order 5 --output-dir mixture_output
dort-mixture mixtures.xlsx --order 5 --validate mixf.cr
```

The first worksheet is used unless `--sheet` selects another. To concentrate
product quadrature directions toward `+z`, `-z`, `+r`, or `-r`, pass
`bias_direction` and `bias_fraction` to `generate_product_quadrature`; see
`docs/source/quadrature_sets.rst`. Example plots show only the positive octant
of the unit sphere, with marker area proportional to angular weight.

## Documentation

The guide starts at `docs/source/index.rst`. Build HTML locally with:

```bash
python -m pip install -e ".[docs]"
DORT_DOCS_OFFLINE=1 make -C docs html
```

Then open `docs/build/html/index.html`. The guide is organized around an
actual modeling workflow; the API reference is reserved for exact signatures.

## Development checks

```bash
python -m pip install -e ".[test]"
python -m pytest
python -m build
```
