# DORT R-Z Input Preparation API

A lightweight Python API for simplifying **DORT R-Z geometry and material filling preparation**.

The main goal is to let the user describe a shielding/reactor model in terms of:

- readable material names,
- radial and axial mesh segments,
- physical R-Z regions,
- simple region priorities,

and let Python handle:

- fine-mesh construction,
- cell-centre material assignment,
- overlap checking,
- material/region maps,
- visual verification,
- DORT material-zone generation,
- FIDO-formatted `2*`, `4*`, `8$`, and `9$` arrays.

> **Project status:** early development. The current API is useful for constructing and checking R-Z material filling and generating the corresponding DORT geometry/material input fragments. It does **not yet generate a complete DORT problem deck**.

---

## 1. Repository structure

The current API is intentionally split into small modules:

```text
.
├── mesh.py
├── materials.py
├── regions.py
├── model.py
├── plotting.py
├── writer.py
├── requirements.txt
├── README.md
├── docs/
│   └── DORT_MAPPING.md
└── examples/
    └── basic_model.py
```

Responsibilities:

| Module | Purpose |
|---|---|
| `mesh.py` | Define and validate R and Z mesh axes |
| `materials.py` | Register named materials and internal material IDs |
| `regions.py` | Define rectangular R-Z regions and generate cell masks |
| `model.py` | Combine mesh, materials, and regions into a final material map |
| `plotting.py` | Plot material and region maps for verification |
| `writer.py` | Convert a built model into DORT/FIDO geometry and material arrays |

---

## 2. Requirements

Python 3.10+ is recommended.

Required Python packages:

```text
numpy
matplotlib
```

Install them with:

```bash
pip install -r requirements.txt
```

At present the repository is not packaged for `pip install`. Run scripts from the repository root, or otherwise ensure the repository root is on `PYTHONPATH`.

---

## 3. Minimal working example

A complete model follows this sequence:

```text
create model
    ↓
add materials
    ↓
define R/Z mesh
    ↓
set background material
    ↓
add physical regions
    ↓
build + validate
    ↓
inspect / plot
    ↓
create DORT writer
    ↓
write DORT arrays
```

Example:

```python
from model import DORTModel
from plotting import plot_materials, plot_regions
from writer import DORTWriter

# ------------------------------------------------------------
# 1. Create model
# ------------------------------------------------------------
model = DORTModel("simple_shield")

# ------------------------------------------------------------
# 2. Register materials
# ------------------------------------------------------------
model.add_material("Sodium")
model.add_material("Core")
model.add_material("SS316")
model.add_material("B4C")
model.add_material("Air")

# ------------------------------------------------------------
# 3. Define R mesh
# ------------------------------------------------------------
model.mesh.r.add_segment(0.0, 100.0, step=5.0)
model.mesh.r.add_segment(100.0, 140.0, step=2.0)
model.mesh.r.add_segment(140.0, 200.0, step=5.0)

# ------------------------------------------------------------
# 4. Define Z mesh
# ------------------------------------------------------------
model.mesh.z.add_segment(-100.0, -50.0, step=5.0)
model.mesh.z.add_segment(-50.0, 50.0, step=2.0)
model.mesh.z.add_segment(50.0, 100.0, step=5.0)

# ------------------------------------------------------------
# 5. Fill the whole domain initially with sodium
# ------------------------------------------------------------
model.set_background("Sodium")

# ------------------------------------------------------------
# 6. Add physical regions
# ------------------------------------------------------------
model.add_region(
    "core",
    material="Core",
    r=(0.0, 100.0),
    z=(-50.0, 50.0),
    priority=20,
)

model.add_region(
    "radial_shield",
    material="SS316",
    r=(100.0, 140.0),
    z=(-50.0, 50.0),
    priority=30,
)

model.add_region(
    "bottom_shield",
    material="B4C",
    r=(0.0, 140.0),
    z=(-100.0, -50.0),
    priority=30,
)

model.add_region(
    "penetration",
    material="Air",
    r=(80.0, 120.0),
    z=(-10.0, 10.0),
    priority=50,
)

# ------------------------------------------------------------
# 7. Build and validate
# ------------------------------------------------------------
summary = model.build()

print(summary)
print(model.material_cell_counts())
print(model.region_cell_counts())

# ------------------------------------------------------------
# 8. Visual verification
# ------------------------------------------------------------
fig, ax = plot_materials(model, show_mesh=True)
fig.savefig("material_map.png", dpi=200, bbox_inches="tight")

fig, ax = plot_regions(model, show_mesh=True)
fig.savefig("region_map.png", dpi=200, bbox_inches="tight")

# ------------------------------------------------------------
# 9. Generate DORT arrays
# ------------------------------------------------------------
writer = DORTWriter(model)

print(writer.summary_text())

writer.write_block4_fragment(
    "geometry_material_fragment.inp"
)
```

---

# 4. Mesh definition

## 4.1 Piecewise-uniform mesh

Each axis is a `MeshAxis`.

```python
model.mesh.r.add_segment(
    start=0.0,
    end=100.0,
    step=2.0,
)
```

This creates:

```text
0, 2, 4, 6, ..., 100
```

Additional segments can be appended:

```python
model.mesh.r.add_segment(100.0, 140.0, step=1.0)
model.mesh.r.add_segment(140.0, 300.0, step=5.0)
```

Segments must be continuous. For example, this is invalid:

```python
model.mesh.r.add_segment(0.0, 100.0, step=5.0)
model.mesh.r.add_segment(110.0, 200.0, step=5.0)
```

because the second segment does not begin where the first one ends.

---

## 4.2 Define a segment by number of cells

Instead of `step`, use `n_cells`:

```python
model.mesh.r.add_segment(
    0.0,
    100.0,
    n_cells=50,
)
```

Specify **either** `step` **or** `n_cells`, not both.

---

## 4.3 Explicit mesh edges

For an irregular mesh:

```python
model.mesh.r.add_edges(
    [0.0, 1.0, 2.0, 5.0, 10.0, 20.0]
)
```

Explicit edges must be strictly increasing.

---

## 4.4 Useful mesh properties

```python
model.mesh.r.edges
model.mesh.r.centers
model.mesh.r.widths
model.mesh.r.n_cells
model.mesh.r.bounds

model.mesh.z.edges
model.mesh.z.centers

model.mesh.shape
model.mesh.n_cells
```

The internal 2-D array convention is:

```text
shape = (nz, nr)
```

or:

```python
array[z_index, r_index]
```

This convention is used consistently by the model and writer.

---

# 5. Materials

Materials are registered using readable names:

```python
model.add_material("Sodium")
model.add_material("SS316")
model.add_material("B4C")
```

Automatic positive IDs are assigned internally.

You can request a particular ID:

```python
model.add_material(
    "Graphite",
    dort_id=20,
    description="Graphite shielding block",
)
```

Access registered materials through:

```python
model.materials["SS316"]
model.materials.get("SS316")
model.materials.get_id("SS316")
model.materials.get_by_id(20)
```

## Important: internal ID vs DORT cross-section material number

`Material.dort_id` is currently a **positive internal identifier**.

Real DORT/GIP libraries may use other material numbers, including negative values. Do not force those values into `MaterialRegistry`.

Instead, override them when creating `DORTWriter`:

```python
writer = DORTWriter(
    model,
    material_numbers={
        "Core": -1,
        "Sodium": -169,
        "SS316": -145,
        "B4C": -181,
        "Air": -117,
    },
)
```

Those values are written into the DORT `9$` array.

---

# 6. Regions

The current geometry primitive is a rectangular R-Z region:

```python
model.add_region(
    "core",
    material="Core",
    r=(0.0, 100.0),
    z=(-50.0, 50.0),
    priority=20,
)
```

Region membership is determined from **mesh-cell centres**:

```text
r_min <= r_center < r_max
z_min <= z_center < z_max
```

The upper bound is exclusive.

This makes adjacent regions sharing a boundary unambiguous.

---

# 7. Background material

For most reactor/shielding models, define a background:

```python
model.set_background("Sodium")
```

The complete mesh is first filled with the background material, then explicit regions overwrite it according to priority.

You can remove the background:

```python
model.clear_background()
```

If no background exists, every cell must be covered by explicit regions unless:

```python
model.build(allow_unfilled=True)
```

is used for debugging.

---

# 8. Priority-based filling

Priority is the main mechanism for handling nested or overlapping geometry.

Example:

```text
background sodium    implicit lowest level
core                 priority 20
radial shield        priority 30
penetration          priority 50
```

The model behaves conceptually like painting layers:

```text
1. fill domain with sodium
2. paint core
3. paint shield
4. paint penetration over anything underneath
```

Higher-priority regions overwrite lower-priority regions.

Example:

```python
model.add_region(
    "core",
    material="Core",
    r=(0, 100),
    z=(-50, 50),
    priority=20,
)

model.add_region(
    "control_rod",
    material="B4C",
    r=(20, 30),
    z=(-50, 50),
    priority=50,
)
```

The control-rod cells become B4C even though they geometrically lie inside the core.

---

## 8.1 Equal-priority overlap

Two regions with the same priority are not allowed to occupy the same mesh cells.

For example:

```python
model.add_region(
    "A",
    material="SS316",
    r=(0, 100),
    z=(0, 100),
    priority=20,
)

model.add_region(
    "B",
    material="B4C",
    r=(50, 150),
    z=(0, 100),
    priority=20,
)
```

`model.build()` will raise an error.

Resolve this by:

- fixing the geometry, or
- deliberately assigning different priorities.

This prevents accidental dependence on insertion order.

---

# 9. Building the model

After defining mesh, materials, and regions:

```python
summary = model.build()
```

The build stage:

1. validates the mesh,
2. validates materials,
3. validates region references,
4. checks region/mesh intersections,
5. checks equal-priority overlaps,
6. fills the background,
7. applies regions from lower to higher priority,
8. checks for unfilled cells,
9. stores the final maps.

The returned object is a `BuildSummary`.

Example:

```python
print(summary)
```

---

## 9.1 Strict region bounds

By default, a region that partly extends beyond the model domain generates a warning.

Use:

```python
model.build(
    strict_region_bounds=True
)
```

to make such cases fatal errors.

---

# 10. Inspecting the built model

The main result arrays are:

```python
model.material_id_map
model.material_name_map
model.region_map
model.priority_map
```

All have shape:

```text
(nz, nr)
```

### `material_id_map`

Internal material IDs:

```python
ids = model.material_id_map
```

### `material_name_map`

Readable names:

```python
names = model.material_name_map
```

### `region_map`

The final region that owns each cell:

```python
owners = model.region_map
```

Background cells contain:

```text
background
```

### `priority_map`

Priority responsible for the final region assignment.

---

# 11. Debugging individual cells

Use:

```python
model.cell_assignment(
    z_index=10,
    r_index=15,
)
```

Example result:

```python
{
    "z_index": 10,
    "r_index": 15,
    "z_center": 5.0,
    "r_center": 95.0,
    "material_id": 5,
    "material": "Air",
    "region": "penetration",
    "priority": 50,
}
```

This is useful when a plotted cell does not have the expected material.

---

# 12. Cell-count summaries

Material counts:

```python
model.material_cell_counts()
```

Example:

```python
{
    "Sodium": 260,
    "Core": 96,
    "SS316": 36,
    "Air": 8,
}
```

Final region ownership:

```python
model.region_cell_counts()
```

A lower-priority region can own fewer cells than its original mask because a higher-priority region may overwrite part of it.

---

# 13. Plotting and verification

Always inspect the model before writing DORT input.

## 13.1 Material map

```python
from plotting import plot_materials

fig, ax = plot_materials(
    model,
    show_mesh=True,
)

fig.savefig(
    "material_map.png",
    dpi=200,
    bbox_inches="tight",
)
```

For small meshes, display the internal material IDs:

```python
fig, ax = plot_materials(
    model,
    show_mesh=True,
    show_ids=True,
)
```

---

## 13.2 Region map

```python
from plotting import plot_regions

fig, ax = plot_regions(
    model,
    show_mesh=True,
)
```

The region plot can distinguish two geometrically different regions that use the same physical material.

---

## 13.3 Convenience save functions

```python
from plotting import (
    save_material_plot,
    save_region_plot,
)

save_material_plot(
    model,
    "material_map.png",
    show_mesh=True,
)

save_region_plot(
    model,
    "region_map.png",
    show_mesh=True,
)
```

---

# 14. DORT writer

Create a writer only **after** the model has been built:

```python
from writer import DORTWriter

writer = DORTWriter(model)
```

Calling the writer before `model.build()` raises an error.

---

# 15. DORT zone policy

DORT distinguishes a **material zone** from the **material number** used by that zone.

The writer supports two policies.

## 15.1 `zone_policy="region"` — recommended

```python
writer = DORTWriter(
    model,
    zone_policy="region",
)
```

Each final geometric owner gets a separate DORT zone.

Example:

```text
Zone 1 -> background    -> Sodium
Zone 2 -> core          -> Core
Zone 3 -> shield        -> SS316
Zone 4 -> vessel        -> SS316
```

Zones 3 and 4 can therefore use the same material while remaining separate DORT zones.

This is the recommended default for shielding models.

---

## 15.2 `zone_policy="material"`

```python
writer = DORTWriter(
    model,
    zone_policy="material",
)
```

All cells containing the same material share one zone.

This reduces the number of DORT zones (`IZM`) but loses geometric-region identity.

---

# 16. DORT arrays generated by the writer

The writer currently generates the geometry/material arrays:

```text
2*   Z fine-mesh boundaries
4*   R fine-mesh boundaries
8$   material zone by fine-space cell
9$   material number by material zone
```

It can additionally generate a simple identity `84$` array:

```text
84$  edit region by material zone
```

where edit-region number equals material-zone number.

---

## 16.1 `2*` Z mesh

```python
print(writer.array2())
```

---

## 16.2 `4*` R mesh

```python
print(writer.array4())
```

---

## 16.3 `8$` zone map

```python
print(writer.array8())
```

The writer compresses the array using FIDO repetition operators:

- `R` for repeated values inside a row,
- `Q` for repeated complete radial rows.

---

## 16.4 `9$` zone-to-material mapping

```python
print(writer.array9())
```

---

## 16.5 Identity `84$`

```python
print(writer.array84_identity())
```

Use this only when one edit region per material zone is the intended DORT setup.

---

# 17. Important DORT array ordering

The internal array has:

```text
shape = (JM, IM) = (nz, nr)
```

For DORT `IJZN(I,J)`:

```text
I = R index
J = Z index
```

The writer serializes:

```text
J = 1: I = 1, 2, ..., IM
J = 2: I = 1, 2, ..., IM
...
```

Therefore:

```python
writer.zone_map.ravel(order="C")
```

is the expanded DORT `8$` stream.

You can inspect it directly:

```python
stream = writer.ijzn_stream()
```

Its length must be:

```python
writer.im * writer.jm
```

---

# 18. Check required `62$` control values

The writer does not currently rewrite the full DORT `62$` array.

It reports the values that must be consistent:

```python
writer.required_control_values
```

Example:

```python
{
    "IZM": 5,
    "IM": 88,
    "JM": 75,
    "INGEOM": 1,
}
```

Before running DORT, ensure that the corresponding `62$` entries in the full deck agree with these values.

You can print a complete summary:

```python
print(writer.summary_text())
```

---

# 19. Writing a Block-4 fragment

Generate:

```text
2*
4*
8$
9$
```

using:

```python
writer.write_block4_fragment(
    "geometry_material_fragment.inp"
)
```

By default no terminating `T` is written because a real DORT Block 4 may contain additional arrays such as source/fission/energy/activity information.

If these arrays are truly the final arrays in Block 4:

```python
writer.write_block4_fragment(
    "geometry_material_fragment.inp",
    terminate_block=True,
)
```

---

## 19.1 Excluding mesh arrays

If the existing DORT input already contains the correct `2*` and `4*` arrays and you only want new material filling:

```python
writer.write_block4_fragment(
    "material_only.inp",
    include_mesh=False,
)
```

This writes only:

```text
8$
9$
```

---

# 20. Recommended workflow for real calculations

For an actual reactor/shielding model:

```text
1. Build the R/Z mesh
2. Register all material names
3. Set the background
4. Add major regions
5. Add nested structures with higher priority
6. model.build()
7. inspect model.warnings
8. plot material map
9. plot region map
10. inspect material/region cell counts
11. inspect suspicious cells if necessary
12. create DORTWriter
13. supply real cross-section material-number mapping
14. check writer.summary_text()
15. verify IZM/IM/JM in 62$
16. write or paste the generated arrays into the complete DORT deck
17. run DORT and check its input-array echo
```

Do **not** skip the visual verification stage for a large model.

---

# 21. Full example with external DORT material numbers

```python
from model import DORTModel
from plotting import save_material_plot
from writer import DORTWriter

model = DORTModel("reactor_case")

for name in (
    "Sodium",
    "Core",
    "SS316",
    "B4C",
    "Air",
):
    model.add_material(name)

model.mesh.r.add_segment(0, 100, step=2)
model.mesh.r.add_segment(100, 140, step=1)
model.mesh.r.add_segment(140, 300, step=5)

model.mesh.z.add_segment(-100, -50, step=5)
model.mesh.z.add_segment(-50, 50, step=2)
model.mesh.z.add_segment(50, 150, step=5)

model.set_background("Sodium")

model.add_region(
    "core",
    material="Core",
    r=(0, 100),
    z=(-50, 50),
    priority=20,
)

model.add_region(
    "radial_shield",
    material="SS316",
    r=(100, 140),
    z=(-50, 50),
    priority=30,
)

model.add_region(
    "bottom_B4C",
    material="B4C",
    r=(0, 140),
    z=(-100, -50),
    priority=30,
)

model.add_region(
    "penetration",
    material="Air",
    r=(80, 120),
    z=(-10, 10),
    priority=50,
)

summary = model.build()

if summary.warnings:
    print("Warnings:")
    for warning in summary.warnings:
        print(" -", warning)

save_material_plot(
    model,
    "material_map.png",
    show_mesh=True,
)

writer = DORTWriter(
    model,
    zone_policy="region",
    material_numbers={
        "Core": -1,
        "Sodium": -169,
        "SS316": -145,
        "B4C": -181,
        "Air": -117,
    },
)

print(writer.summary_text())

writer.write_block4_fragment(
    "geometry_material_fragment.inp"
)
```

---

# 22. Common errors

## `Material '...' is not registered`

Cause: a region refers to a material that was never added.

Fix:

```python
model.add_material("SS316")
```

before adding/building the region.

---

## `Segments must be continuous`

Cause:

```python
mesh.r.add_segment(0, 100, step=5)
mesh.r.add_segment(110, 200, step=5)
```

Fix the second start coordinate:

```python
mesh.r.add_segment(100, 200, step=5)
```

---

## `step does not divide the interval exactly`

Example:

```python
mesh.r.add_segment(0, 10, step=3)
```

would create an unwanted shortened final cell.

Use either a compatible step:

```python
mesh.r.add_segment(0, 10, step=2)
```

or explicit edges:

```python
mesh.r.add_edges([0, 3, 6, 9, 10])
```

---

## `Equal-priority overlap detected`

Two regions with the same priority select common mesh cells.

Check whether:

- the overlap is accidental, or
- one region should intentionally overwrite the other.

For intentional overwrite, give the later physical feature a higher priority.

---

## `Model contains ... unfilled mesh cells`

Define a background:

```python
model.set_background("Sodium")
```

or add regions covering all cells.

Use `allow_unfilled=True` only for debugging.

---

## `DORTWriter requires a built model`

Call:

```python
model.build()
```

before:

```python
writer = DORTWriter(model)
```

---

# 23. Current limitations

The following are **not yet implemented**:

- full automatic DORT deck generation,
- automatic update/replacement of `62$`,
- automatic insertion into an existing template deck,
- arbitrary non-rectangular region primitives,
- curved boundaries beyond the rectangular R-Z cell-centre representation,
- fractionally mixed cells at region boundaries,
- DORT variable-I mesh (`IM < 0`),
- coarse-mesh (`85*`, `86*`) generation,
- quadrature generation,
- cross-section mixing (`10$`, `11$`, `12*`, `13$`) generation,
- source definition,
- energy-group arrays,
- automatic execution of DORT,
- parsing/validation of a complete DORT output.

The current API targets the **R-Z mesh and material-filling preparation problem first**.

---

# 24. Design philosophy

The API intentionally separates:

```text
physical model
    ↓
mesh-cell representation
    ↓
DORT representation
```

A user should describe:

```text
"this region is SS316"
```

instead of manually constructing hundreds of thousands of DORT zone entries.

The code then converts:

```text
physical region
    ↓
Boolean mesh mask
    ↓
final region/material map
    ↓
DORT zone map
    ↓
FIDO input
```

---

# 25. Suggested next development steps

A logical roadmap is:

1. **Template/deck module**
   - read an existing DORT deck,
   - replace `2*`, `4*`, `8$`, `9$`, and optionally `84$`,
   - update `IZM`, `IM`, and `JM` in `62$`.

2. **Additional geometry primitives**
   - axial layer,
   - radial annulus,
   - convenience vessel/shield functions.

3. **Material-library integration**
   - explicit mapping to GIP/DORT cross-section identifiers.

4. **Excel/YAML frontend**
   - translate tabular input into the same Python API.

5. **Automated tests**
   - mesh tests,
   - overlap tests,
   - FIDO expansion round-trip tests,
   - comparison against known DORT inputs/outputs.

---

# 26. Reference

The implementation of the writer follows the DORT 3.1 input-array concepts used by this project, especially the distinction between:

- fine-space mesh boundaries,
- material-zone assignment `IJZN(I,J)`,
- zone-to-material mapping `IZMT(IZ)`.

When modifying the writer, always verify generated array lengths and ordering against the DORT input echo/output for a known problem.

---

## License

No license is included automatically in this repository. Add a `LICENSE` file appropriate for your intended distribution before making the project broadly reusable.
