# Human-readable run controls

This revision keeps DORT's original 61$$/62$$ names as an internal serialization
layer but exposes descriptive names to normal users.

## Typical use

```python
run = writer.create_run_control(
    "eigenvalue_first",
    energy_groups=217,
    quadrature_directions=48,
    neutron_groups=175,
    maximum_outer_iterations=20,
    left_boundary="reflected",
    right_boundary="void",
    flux_extrapolation="theta_weighted",
)

run.configure(
    initial_inner_iterations=30,
    final_inner_iterations=20,
    scalar_flux_printing="after_each_group",
    cross_section_printing="suppress",
)
```

## Discoverability

```python
run.available_options("left_boundary")
run.describe_setting("flux_extrapolation")
print(run.settings_help())
current = run.settings
```

The help table includes the underlying DORT variable only as a reference.

## Advanced escape hatch

For local DORT variables not yet represented by a descriptive setting:

```python
run.set_raw_dort62(LOCOBJ=0, LCMOBJ=0)
```

The old `set62()` method remains as a legacy alias.
