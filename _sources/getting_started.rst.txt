Getting Started
===============

The API is designed to separate three layers:

.. code-block:: text

   physical model
       ↓
   mesh-cell representation
       ↓
   DORT representation

The user should describe physical intent, for example:

.. code-block:: text

   "this region is SS316"

rather than manually creating thousands of DORT zone entries.

The current conversion chain is:

.. code-block:: text

   physical region
       ↓
   Boolean mesh mask
       ↓
   final region/material map
       ↓
   DORT zone map
       ↓
   FIDO input

Minimal example
---------------

.. code-block:: python

   from model import DORTModel
   from plotting import plot_materials, plot_regions
   from writer import DORTWriter

   model = DORTModel("simple_shield")

   # Materials
   for name in ("Sodium", "Core", "SS316", "B4C", "Air"):
       model.add_material(name)

   # R mesh
   model.mesh.r.add_segment(0.0, 100.0, step=5.0)
   model.mesh.r.add_segment(100.0, 140.0, step=2.0)
   model.mesh.r.add_segment(140.0, 200.0, step=5.0)

   # Z mesh
   model.mesh.z.add_segment(-100.0, -50.0, step=5.0)
   model.mesh.z.add_segment(-50.0, 50.0, step=2.0)
   model.mesh.z.add_segment(50.0, 100.0, step=5.0)

   # Background
   model.set_background("Sodium")

   # Regions
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

   # Verify the model visually before exporting.
   fig, ax = plot_materials(model, show_mesh=True)
   fig.savefig("material_map.png", dpi=200, bbox_inches="tight")

   fig, ax = plot_regions(model, show_mesh=True)
   fig.savefig("region_map.png", dpi=200, bbox_inches="tight")

   # Generate DORT arrays.
   writer = DORTWriter(model)
   print(writer.summary_text())

   writer.write_block4_fragment("geometry_material_fragment.inp")

Quadrature stage
----------------

Angular quadrature should be treated as a distinct input-preparation stage
after the spatial model has been verified. For DORT-compatible serialization,
the calculated set must ultimately provide the directional weights and the R
and Z direction cosines used by ``81*``, ``82*`` and ``83*``.

See :doc:`user_guide/quadrature` for the DORT mapping and compatibility notes.

Recommended practice
--------------------

For production models, do not skip visual verification. Inspect warnings,
material/region cell counts, and any suspicious cells before generating the
DORT fragment.
