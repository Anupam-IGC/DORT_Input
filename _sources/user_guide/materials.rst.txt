Materials
=========

Registering materials
---------------------

Materials are registered by readable names:

.. code-block:: python

   model.add_material("Sodium")
   model.add_material("SS316")
   model.add_material("B4C")

The registry assigns positive internal IDs automatically.

A specific internal ID and description may be requested:

.. code-block:: python

   model.add_material(
       "Graphite",
       dort_id=20,
       description="Graphite shielding block",
   )

Registry access
---------------

.. code-block:: python

   model.materials["SS316"]
   model.materials.get("SS316")
   model.materials.get_id("SS316")
   model.materials.get_by_id(20)

Internal material IDs versus DORT library numbers
-------------------------------------------------

``Material.dort_id`` is currently a positive internal identifier. It should not
be assumed to be identical to the material number used by a DORT/GIP
cross-section library.

When generating DORT input, supply the actual DORT material numbers explicitly:

.. code-block:: python

   from writer import DORTWriter

   writer = DORTWriter(
       model,
       material_numbers={
           "Core": -1,
           "Sodium": -169,
           "SS316": -145,
           "B4C": -181,
           "Air": -117,
       },
   )

These values are written into the DORT ``9$`` array.
