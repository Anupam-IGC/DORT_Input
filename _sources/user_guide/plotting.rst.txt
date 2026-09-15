Plotting and Visual Verification
================================

Visual inspection is an important validation step before DORT input is
generated.

Material map
------------

.. code-block:: python

   from plotting import plot_materials

   fig, ax = plot_materials(
       model,
       show_mesh=True,
   )

   fig.savefig(
       "material_map.png",
       dpi=200,
       bbox_inches="tight",
   )

For small meshes, show internal material IDs:

.. code-block:: python

   fig, ax = plot_materials(
       model,
       show_mesh=True,
       show_ids=True,
   )

Region map
----------

.. code-block:: python

   from plotting import plot_regions

   fig, ax = plot_regions(
       model,
       show_mesh=True,
   )

The region view is useful when distinct geometric regions use the same
physical material.

Convenience save functions
--------------------------

.. code-block:: python

   from plotting import (
       save_material_plot,
       save_region_plot,
   )

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

Recommended verification
------------------------

For a large model, inspect at least:

* warnings returned by the build,
* material and region plots,
* material and region cell counts,
* suspicious cells using ``cell_assignment``.
