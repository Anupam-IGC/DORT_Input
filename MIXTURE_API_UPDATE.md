# External Mixture API — Local DORT Workflow

## Corrected interpretation

The supplied local workflow does not use stock DORT in-core mixing cards
`10$`, `11$`, and `12*` to form macroscopic materials. Instead, the external
program `m_ia_oa.for` reads microscopic cross sections from `igc-s3` and a
simple composition file `mix.inp`, then writes the macroscopic file `mixf.cr`.

`mixf.cr` is supplied to the modified DORT as the NTSIG cross-section file on
logical unit 51 in the sample setup.

## Numbering

For Legendre order `L`, every physical mixture contributes `L+1` complete
cross-section tables. For mixture ID `m`:

```text
first_table(m) = 1 + (m - 1) * (L + 1)
9$ reference   = -first_table(m)
```

For P5:

```text
m=1 -> 1..6   -> -1
m=2 -> 7..12  -> -7
m=3 -> 13..18 -> -13
```

## API

```python
model.add_mixture(
    "Steel",
    {5125: 1.10597e-2, 5131: 8.27546e-3, 825: 2.90028e-2},
    legendre_order=5,
)

model.write_mixture_input("mix.inp")
model.validate_mixture_file("mixf.cr")
```

The DORT writer derives the negative 9$ reference automatically and provides a
61$ helper whose third value is NTSIG:

```python
writer = DORTWriter(model, cross_section_unit=51)
print(writer.array61())
print(writer.array9())
```

## External program limits encoded in validation

From the supplied `m_ia_oa.for`:

- maximum mixtures: 70
- maximum components per mixture: 20
- maximum distinct microscopic MAT numbers: 112
- maximum Legendre order: 6
- energy groups: 217
- columns per energy group: 220
- values per cross-section table: 47,740
