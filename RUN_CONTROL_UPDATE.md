# Human-readable run-control update

The run-control API now separates the public configuration vocabulary from
DORT's internal `61$$`/`62$$` variable names.

The three verified presets remain:

- `eigenvalue_first`
- `eigenvalue_rerun`
- `fixed_source`

Normal changes now use descriptive settings, for example:

```python
run.configure(
    maximum_outer_iterations=20,
    left_boundary="reflected",
    right_boundary="void",
    flux_extrapolation="theta_weighted",
    scalar_flux_printing="after_each_group",
)
```

Option discovery is built into the object:

```python
run.available_options("left_boundary")
run.describe_setting("starting_flux")
run.settings_help()
run.settings
```

The raw DORT names remain accessible only when needed through
`set_raw_dort62(...)`; `set62(...)` is retained as a legacy alias.

The public setting layer includes starting-flux/source representations, R-Z
boundary conditions, iteration limits, flux extrapolation, rebalance method,
printing/output behavior, zone convergence, fission treatment, cross-section
format, key-flux indices and automatically derived geometry controls.
