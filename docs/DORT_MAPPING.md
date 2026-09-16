# DORT mapping used by the local API

This note is a compact cross-check for the locally modified DORT workflow. The
more readable version is available in the Sphinx page
`docs/source/user_guide/dort_mapping.rst`.

## Internal R-Z ordering

```text
shape = (JM, IM) = (nz, nr)
array[z_index, r_index]
```

When serialized, the radial `I` index varies fastest inside each axial `J` row.

## Main geometry/material arrays

| Card | Meaning |
|---|---|
| `2*` | Z fine-mesh boundaries |
| `4*` | R fine-mesh boundaries |
| `8$` | material-zone number by fine-space cell |
| `9$` | local cross-section reference by material zone |
| `84$` | edit-region number by material zone |

## External-mixture `9$` convention

For mixture ID `m` and Legendre order `L`, the external mixer writes `L+1`
consecutive tables beginning at

```text
t_m = 1 + (m - 1) * (L + 1)
```

The locally modified DORT uses

```text
IZMT = -t_m
```

so P5 mixtures are referenced as `-1, -7, -13, -19, ...`.

This convention is specific to the verified local `mixf.cr` workflow and is not
the stock DORT in-core mixing convention.

## Cross-section unit

The third entry of `61$$` is `NTSIG`. The verified sample uses:

```text
NTSIG = 51
file  = mixf.cr
```

## Edit-region helpers

- `writer.array84_identity()` gives edit regions `1..IZM`.
- `writer.array84_by_material()` groups zones by natural API material ID.

`84$` is an edit-region mapping, not a cross-section-material numbering card.
