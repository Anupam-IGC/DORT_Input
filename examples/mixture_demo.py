"""Reproduce the supplied mix.inp and local DORT mixture references."""

from model import DORTModel
from writer import DORTWriter


model = DORTModel("external_mixture_sample")
model.add_mixture(
    "Mixture-1",
    {5125: 1.10597e-2, 5131: 8.27546e-3, 825: 2.90028e-2},
    legendre_order=5,
)
model.add_mixture("Mixture-2", {425: 1.1107e-1})
model.add_mixture("Mixture-3", {725: 1.89693e-5, 825: 8.15551e-5})

print(model.render_mixture_input())
model.write_mixture_input("mix.inp")

# Geometry can then use the same mixture names.
model.mesh.r.add_segment(0.0, 30.0, step=10.0)
model.mesh.z.add_segment(-20.0, 20.0, step=10.0)
model.set_background("Mixture-1")
model.add_region(
    "centre",
    material="Mixture-2",
    r=(0.0, 10.0),
    z=(-10.0, 10.0),
    priority=10,
)
model.add_region(
    "outer",
    material="Mixture-3",
    r=(20.0, 30.0),
    z=(-20.0, 20.0),
    priority=20,
)
model.build()

writer = DORTWriter(model, cross_section_unit=51)
print(writer.array61())
print(writer.array9())
print(writer.material_layout_text())
