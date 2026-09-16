"""Illustrate human-readable DORT run-control settings."""

from model import DORTModel
from writer import DORTWriter

model = DORTModel("run_mode_demo")
model.add_mixture("Material-1", {425: 1.0e-2}, legendre_order=5)
model.mesh.r.add_segment(0.0, 20.0, step=2.0)
model.mesh.z.add_segment(-10.0, 10.0, step=2.0)
model.set_background("Material-1")
model.build()

writer = DORTWriter(model, cross_section_unit=51)

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

print(run.summary_text())
print()
print(run.settings_help())
print()
print("Boundary choices:", run.available_options("left_boundary"))
print()
print(run.describe_setting("starting_flux"))

run.configure(
    scalar_flux_printing="after_each_group",
    cross_section_printing="suppress",
    initial_inner_iterations=30,
    final_inner_iterations=20,
)

print()
print(run.control_fragment())
