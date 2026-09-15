# DORT Quadrature Module

`quadrature.py` generates directional quadrature sets for DORT without exposing
the terse control-variable names used by the historical Fortran generator.

The module supports two quadrature families:

- **legacy** — reproduces the historical DOQDP moment-fitted construction.
  Use this when reproducing an established DORT calculation.
- **product** — positive-weight Gauss product quadrature intended for higher
  angular resolution. Use this for new high-order calculations.

## Quick start

### Reproduce a conventional S8 set

```python
from quadrature import generate_legacy_quadrature

quadrature = generate_legacy_quadrature(
    order=8,
    symmetry="half",
)

print(quadrature.summary_text())
print(quadrature.validation_text())

quadrature.write_dort("quadrature_s8.inc")
```

### Generate a modern high-order set

```python
from quadrature import generate_product_quadrature

quadrature = generate_product_quadrature(
    polar_order=24,
    azimuthal_order=32,
)

print(quadrature.summary_text())
print(quadrature.validation_text())

quadrature.write_dort("quadrature_24x32.inc")
```

The 24×32 example contains:

```text
24 axial-cosine levels
768 nonzero integration directions
24 zero-weight level initiators
792 total DORT directions
```

Therefore the corresponding DORT `MM` value is `792`.

## Public terminology

The modern module uses descriptive names:

| Python name | Meaning |
|---|---|
| `order` | Legacy S_N order |
| `symmetry` | `"none"`, `"half"`, or `"full"` |
| `radial_cosine_levels` | Positive first-dimension direction-cosine levels |
| `axial_cosine_levels` | Positive second-dimension direction-cosine levels |
| `smallest_radial_cosine` | Seed used to generate legacy cosine levels |
| `moment_pairs` | `(radial_power, axial_power)` fitted moments |
| `polar_order` | Number of product-quadrature axial levels |
| `azimuthal_order` | Number of product integration directions per axial level |

The old integer flags are intentionally **not part of the public API**.

DORT's standard names `MU` and `ETA` are retained only as read-only aliases:

```python
quadrature.mu
quadrature.eta
```

The clearer names are:

```python
quadrature.radial_cosine
quadrature.axial_cosine
```

## Legacy quadrature

Use the legacy family when numerical compatibility with an older input is
important.

```python
quadrature = generate_legacy_quadrature(
    order=8,
    symmetry="half",
)
```

### Explicit radial levels

```python
quadrature = generate_legacy_quadrature(
    order=8,
    symmetry="half",
    radial_cosine_levels=[
        0.9511897312,
        0.7867957925,
        0.5773502692,
        0.2182178902,
    ],
)
```

### Generate levels from one seed

```python
quadrature = generate_legacy_quadrature(
    order=8,
    symmetry="half",
    smallest_radial_cosine=0.2182178902,
)
```

If the seed is omitted, the historical recommended value is used:

```text
sqrt(1 / (3*order - 3))
```

### Separate axial levels

```python
quadrature = generate_legacy_quadrature(
    order=8,
    radial_cosine_levels=[...],
    axial_cosine_levels=[...],
)
```

If `axial_cosine_levels` is omitted, the radial levels are reused.

### User-selected moments

```python
quadrature = generate_legacy_quadrature(
    order=8,
    symmetry="half",
    moment_pairs=[
        (0, 0),
        (2, 0),
        (4, 0),
        (6, 0),
        (2, 2),
        (4, 2),
    ],
)
```

Normally this argument should be omitted and the legacy moment selection
algorithm will be used automatically.

## Why not simply use very high legacy S_N order?

The legacy family determines its weights by solving a moment-conservation
linear system. Its conditioning becomes progressively worse as the order
increases, and negative weights can appear.

The generated object reports the condition number:

```python
print(quadrature.metadata["condition_number"])
```

and validation reports negative weights and poor conditioning.

For new high-order calculations, prefer the product family.

## Product quadrature

The modern product family uses:

1. Gauss-Legendre quadrature in the axial cosine over `[-1, 1]`;
2. Gauss-Legendre quadrature in azimuth over the represented DORT half-sphere;
3. one zero-weight initiating direction at the start of each axial level.

```python
quadrature = generate_product_quadrature(
    polar_order=32,
    azimuthal_order=32,
)
```

`polar_order` must currently be even so that negative axial levels precede
positive levels without introducing a zero axial level.

The total DORT direction count is

```text
polar_order * (azimuthal_order + 1)
```

because each axial level has one additional zero-weight initiating direction.

## Validation

Always inspect a generated set before using it:

```python
report = quadrature.validate()

print(report.text())
```

The validator checks:

- total weight is 1;
- direction cosines are physical;
- negative axial levels do not occur after positive levels;
- each axial level is contiguous;
- radial cosines increase within each level;
- each level starts with a zero-weight initiating direction;
- the initiating direction is geometrically correct;
- weighted radial current is zero within every level;
- negative integration weights;
- selected analytical angular moments;
- legacy moment-matrix conditioning.

For the product family, negative weights are errors.

For the legacy family, negative weights are warnings so that old calculations
can still be reproduced.

Useful properties:

```python
quadrature.direction_count
quadrature.integration_direction_count
quadrature.zero_weight_direction_count
quadrature.axial_level_count
quadrature.weight_sum
quadrature.third_cosine
quadrature.maximum_moment_error
```

## DORT output

The module writes:

```text
82*  radial direction cosine
83*  axial direction cosine
81*  directional weight
```

which matches the style of the supplied DORT input.

```python
quadrature.write_dort(
    "quadrature.inc",
    precision=6,
    values_per_line=4,
    terminate_block=False,
)
```

`terminate_block=False` is normally appropriate when additional Block-3
arrays such as `84$`, `85*`, `86*`, or `87$` follow.

To inspect the text without writing:

```python
print(quadrature.dort_text())
```

## Unified dispatcher

You may also use:

```python
from quadrature import generate_quadrature

legacy = generate_quadrature(
    family="legacy",
    order=8,
    symmetry="half",
)

modern = generate_quadrature(
    family="product",
    polar_order=24,
    azimuthal_order=32,
)
```

The two explicit functions are usually clearer in application code.

## Recommended policy

For this DORT input-preparation API:

```text
Existing / benchmark model to reproduce
    -> generate_legacy_quadrature()

New calculation requiring normal angular resolution
    -> legacy S8 / S12 / S16 may be used after validation

New calculation requiring high angular resolution
    -> generate_product_quadrature()
```

Do not select a quadrature only from its nominal order. Always inspect the
validation report and perform a quadrature-convergence study for the physical
problem being solved.
