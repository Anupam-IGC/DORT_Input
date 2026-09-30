Quick Start: Build Your First Model
===================================

This page follows the same model as ``examples/modeling_basics.py``. The goal
is to create a reviewed R-Z material map and write the geometry/material DORT
fragment before adding calculation controls.

1. Create a model and load mixtures
-----------------------------------

Start from a fresh model. Load mixtures before defining regions because the
workbook column order determines material IDs and ``mixf.cr`` table order.

.. code-block:: python

   from dort_input import DORTModel

   model = DORTModel("my_shielding_model")
   model.load_mixtures_from_excel(
       "examples/data/mixtures_example.xlsx",
       legendre_order=5,
   )

For a production case, replace the supplied workbook with your reviewed MAT
numbers and atom densities.

2. Define the R-Z mesh
----------------------

Use finer cells near material interfaces and coarser cells farther away:

.. code-block:: python

   model.mesh.r.add_segment(0.0, 40.0, step=5.0)
   model.mesh.r.add_segment(40.0, 50.0, step=2.0)
   model.mesh.r.add_segment(50.0, 80.0, step=5.0)
   model.mesh.r.add_segment(80.0, 100.0, step=10.0)

   model.mesh.z.add_segment(-100.0, -60.0, step=10.0)
   model.mesh.z.add_segment(-60.0, 60.0, step=5.0)
   model.mesh.z.add_segment(60.0, 100.0, step=10.0)

Every segment must start where the previous segment ended. Region membership
is evaluated at cell centres.

3. Fill the model with named regions
------------------------------------

Set a background first so that every cell has a valid material. Add physical
regions using readable names:

.. code-block:: python

   model.set_background("Sodium")

   model.add_region(
       "central_block",
       material="Graphite",
       r=(0.0, 40.0),
       z=(-40.0, 40.0),
       priority=20,
   )
   model.add_region(
       "steel_vessel",
       material="Carbon Steel",
       r=(40.0, 50.0),
       z=(-60.0, 60.0),
       priority=30,
   )

Higher-priority regions overwrite lower-priority regions. Equal-priority
overlap is rejected because it would make the result depend on definition
order.

4. Build and inspect
--------------------

.. code-block:: python

   summary = model.build(strict_region_bounds=True)

   print(summary)
   print(model.material_cell_counts())
   print(model.region_cell_counts())

Do not proceed merely because ``build()`` succeeded. Plot both the final
material map and region ownership:

.. code-block:: python

   from dort_input.plotting import save_material_plot, save_region_plot

   save_material_plot(model, "materials.png", show_mesh=True)
   save_region_plot(model, "regions.png", show_mesh=True)

Use ``model.cell_assignment(z_index, r_index)`` to investigate a suspicious
cell.

5. Create the DORT writer
-------------------------

.. code-block:: python

   from dort_input import DORTWriter

   writer = DORTWriter(
       model,
       zone_policy="material",
       cross_section_unit=51,
       cross_section_filename="mixf.cr",
   )

   print(writer.material_layout_text())
   print(writer.zone_table_text())
   writer.write_block4_fragment("geometry_material.inc")

The written fragment contains ``2**``, ``4**``, ``8$$``, and ``9$$``. The
default ``zone_policy="material"`` assigns one zone and one ``9$$`` entry to
each used material. ``IZM`` in ``62$$`` then matches that count. The model
still retains the final physical-region map for inspection and source
selection. Select ``zone_policy="region"`` explicitly only when different
regions with the same material must remain separate DORT zones; that policy
repeats their ``9$$`` references and raises ``IZM`` accordingly.

6. Prepare external mixture files
---------------------------------

.. code-block:: python

   model.write_mixture_preparation_files("mixture_output")

This writes:

* ``mix.inp`` for the external mixer;
* ``Mixture_Names.txt`` for human-readable checking;
* ``dort_mix_cards.txt`` for compact mixture mapping.

Run the external mixer to create ``mixf.cr`` and verify its table count before
running DORT. Continue with :doc:`mixtures` for details.

Run the complete tutorial
-------------------------

.. code-block:: bash

   python examples/modeling_basics.py

The script includes all the steps above and produces reviewable plots and
fragments. Once it works, copy the script and change only one layer at a time:
workbook, mesh, regions, then calculation controls.
