Regions and Priority Filling
============================

Rectangular R-Z regions
-----------------------

The current geometry primitive is a rectangular R-Z region:

.. code-block:: python

   model.add_region(
       "core",
       material="Core",
       r=(0.0, 100.0),
       z=(-50.0, 50.0),
       priority=20,
   )

Cell-centre membership
----------------------

Region membership is evaluated at mesh-cell centres:

.. code-block:: text

   r_min <= r_center < r_max
   z_min <= z_center < z_max

The upper boundary is exclusive. This makes adjacent regions that share a
boundary unambiguous.

Background material
-------------------

For most reactor and shielding models, define a background:

.. code-block:: python

   model.set_background("Sodium")

The full mesh is first filled with this material. Explicit regions then
overwrite the background according to their priorities.

Remove the background with:

.. code-block:: python

   model.clear_background()

If no background exists, all mesh cells must be covered unless debugging with:

.. code-block:: python

   model.build(allow_unfilled=True)

Priority model
--------------

Priority handles nested or overlapping geometry. Higher-priority regions
overwrite lower-priority regions.

For example:

.. code-block:: python

   model.add_region(
       "core",
       material="Core",
       r=(0, 100),
       z=(-50, 50),
       priority=20,
   )

   model.add_region(
       "control_rod",
       material="B4C",
       r=(20, 30),
       z=(-50, 50),
       priority=50,
   )

The control-rod cells are assigned ``B4C`` even though the rod lies inside the
core.

Equal-priority overlap
----------------------

Two regions with the same priority may not occupy the same cells. Such an
overlap raises an error during ``model.build()``.

This prevents the final result from depending silently on insertion order.
Resolve the overlap by fixing the geometry or by assigning different
priorities when one feature is intended to overwrite another.
