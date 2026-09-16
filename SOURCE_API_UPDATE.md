# Fixed-Source Spatial API Update

This update adds `source.py` and integrates it with `writer.py` and
`run_control.py` for the locally verified `INPSRM=2` fixed-source workflow.

## User-facing workflow

```python
source = writer.create_source(background=1.0e-20)
source.by_material("Fuel", strength=1.0)
source.set_energy_spectrum_file("source_spectrum.txt")

run = writer.create_run_control(
    "fixed_source",
    energy_groups=217,
    quadrature_directions=210,
)
run.attach_source(source)

print(run.source_fragment())
```

## Spatial selectors

- `by_material(...)` — final material map
- `by_region(...)` — final region/owner map
- `by_zone(...)` — generated DORT material zone
- `by_mesh(r=..., z=...)` — cell-centre R-Z selection
- `set_spatial_array(...)` — direct `(JM, IM)` array
- `set_spatial_function(...)` — arbitrary `f(r,z)` at cell centres

Selections default to replacement; `combine="add"` and
`combine="multiply"` are also available.

## Energy spectrum

`set_energy_spectrum_file()` accepts plain numeric text, Fortran D exponents,
and simple FIDO repetition such as `42R 0.0`.  It may also read text containing
a leading `98**` and trailing `t`/`e` marker.  Normalization is optional and is
off by default.

## DORT output

- `source.array96()` generates the spatial source with R/Q compression.
- `source.array98()` generates the group spectrum.
- `source.fragment()` returns both cards.
- `run.attach_source(source)` validates source shape and group count.
- `run.source_fragment()` returns the attached source cards.
- `run.control_and_source_fragment()` returns 61$$/62$$/63** plus 96**/98**.

The high-level source builder intentionally targets the verified `INPSRM=2`
space-energy form.  It does not generate card 97**.
