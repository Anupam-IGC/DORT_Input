Basic Model Example
===================

This example constructs a small R-Z shielding model and writes the
geometry/material fragment.

.. code-block:: python

   from model import DORTModel
   from plotting import save_material_plot, save_region_plot
   from writer import DORTWriter

   model = DORTModel("simple_shield")

   for name in ("Sodium", "Core", "SS316", "B4C", "Air"):
       model.add_material(name)

   model.mesh.r.add_segment(0.0, 100.0, step=5.0)
   model.mesh.r.add_segment(100.0, 140.0, step=2.0)
   model.mesh.r.add_segment(140.0, 200.0, step=5.0)

   model.mesh.z.add_segment(-100.0, -50.0, step=5.0)
   model.mesh.z.add_segment(-50.0, 50.0, step=2.0)
   model.mesh.z.add_segment(50.0, 100.0, step=5.0)

   model.set_background("Sodium")

   model.add_region(
       "core",
       material="Core",
       r=(0.0, 100.0),
       z=(-50.0, 50.0),
       priority=20,
   )

   model.add_region(
       "radial_shield",
       material="SS316",
       r=(100.0, 140.0),
       z=(-50.0, 50.0),
       priority=30,
   )

   model.add_region(
       "bottom_shield",
       material="B4C",
       r=(0.0, 140.0),
       z=(-100.0, -50.0),
       priority=30,
   )

   model.add_region(
       "penetration",
       material="Air",
       r=(80.0, 120.0),
       z=(-10.0, 10.0),
       priority=50,
   )

   summary = model.build()
   print(summary)
   print(model.material_cell_counts())
   print(model.region_cell_counts())

   save_material_plot(
       model,
       "material_map.png",
       show_mesh=True,
   )

   save_region_plot(
       model,
       "region_map.png",
       show_mesh=True,
   )

   writer = DORTWriter(model)
   print(writer.summary_text())

   writer.write_block4_fragment(
       "geometry_material_fragment.inp"
   )
