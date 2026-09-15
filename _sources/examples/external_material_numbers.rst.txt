Using DORT Cross-Section Material Numbers
=========================================

The internal material IDs used by the Python model do not need to match the
material numbers used by the DORT/GIP cross-section library.

Supply the library-specific mapping to ``DORTWriter``:

.. code-block:: python

   from model import DORTModel
   from plotting import save_material_plot
   from writer import DORTWriter

   model = DORTModel("reactor_case")

   for name in (
       "Sodium",
       "Core",
       "SS316",
       "B4C",
       "Air",
   ):
       model.add_material(name)

   model.mesh.r.add_segment(0, 100, step=2)
   model.mesh.r.add_segment(100, 140, step=1)
   model.mesh.r.add_segment(140, 300, step=5)

   model.mesh.z.add_segment(-100, -50, step=5)
   model.mesh.z.add_segment(-50, 50, step=2)
   model.mesh.z.add_segment(50, 150, step=5)

   model.set_background("Sodium")

   model.add_region(
       "core",
       material="Core",
       r=(0, 100),
       z=(-50, 50),
       priority=20,
   )

   model.add_region(
       "radial_shield",
       material="SS316",
       r=(100, 140),
       z=(-50, 50),
       priority=30,
   )

   model.add_region(
       "bottom_B4C",
       material="B4C",
       r=(0, 140),
       z=(-100, -50),
       priority=30,
   )

   model.add_region(
       "penetration",
       material="Air",
       r=(80, 120),
       z=(-10, 10),
       priority=50,
   )

   summary = model.build()

   if summary.warnings:
       print("Warnings:")
       for warning in summary.warnings:
           print(" -", warning)

   save_material_plot(
       model,
       "material_map.png",
       show_mesh=True,
   )

   writer = DORTWriter(
       model,
       zone_policy="region",
       material_numbers={
           "Core": -1,
           "Sodium": -169,
           "SS316": -145,
           "B4C": -181,
           "Air": -117,
       },
   )

   print(writer.summary_text())

   writer.write_block4_fragment(
       "geometry_material_fragment.inp"
   )
