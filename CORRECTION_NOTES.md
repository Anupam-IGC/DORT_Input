# Correction to the Previous Mixture API

The earlier mixture implementation based on stock DORT arrays 10$/11$/12* is
superseded by this update.

After inspection of the supplied local files:

- `m_ia_oa.for`
- `mix.inp`
- `mixf.cr`

this project now follows the actual local workflow:

1. `mix.inp` specifies Legendre order, mixtures, microscopic MAT numbers and atom densities.
2. `m_ia_oa.for` reads microscopic `igc-s3` tables.
3. It forms macroscopic cross sections and writes `L+1` tables per mixture to `mixf.cr`.
4. The locally modified DORT reads `mixf.cr` as its cross-section input on NTSIG logical unit 51.
5. Array `9$$` uses the negative first table number for each mixture: `-1, -7, -13, ...` for P5.

The corrected API therefore generates `mix.inp`, validates `mixf.cr`, derives
negative `9$$` references, and provides a `61$$` helper. It does not generate
stock DORT 10$/11$/12* mixing cards.
