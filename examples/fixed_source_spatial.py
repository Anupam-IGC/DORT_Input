"""Example: fixed-source spatial distribution from an existing DORT model."""

from model import DORTModel
from writer import DORTWriter

model = DORTModel("fixed_source_demo")
model.add_mixture("Sodium", {1125: 2.5e-2}, legendre_order=5)
model.add_mixture("Fuel", {9225: 1.0e-2})

model.mesh.r.add_segment(0.0, 100.0, step=10.0)
model.mesh.z.add_segment(-50.0, 50.0, step=10.0)
model.set_background("Sodium")
model.add_region(
    "fuel_region",
    material="Fuel",
    r=(0.0, 40.0),
    z=(-20.0, 20.0),
    priority=20,
)
model.build()

writer = DORTWriter(model, cross_section_unit=51)

# Use a tiny non-zero background, matching the style of the verified local deck.
source = writer.create_source(background=1.0e-20)
source.by_region("fuel_region", strength=1.0)
source.set_energy_spectrum_file("source_spectrum.txt")

run = writer.create_run_control(
    "fixed_source",
    energy_groups=217,
    quadrature_directions=210,
)
run.attach_source(source)

print(source.summary_text())
print(run.card_policy.summary_text())
print(run.source_fragment())
