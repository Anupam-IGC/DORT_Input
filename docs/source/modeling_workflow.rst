Modeling Workflow
=================

A reliable DORT input is easier to review when it is built in layers. The
recommended sequence below prevents geometry, cross-section, and run-control
decisions from becoming mixed together.

A typical script begins with:

.. code-block:: python

   from dort_input import DORTModel, DORTWriter, generate_legacy_quadrature
   from dort_input.plotting import (save_material_plot,
                                   save_material_region_union_plot,
                                   save_region_plot, write_outline_csv)

Step 1: decide the calculation basis
------------------------------------

Before writing Python, record:

* calculation type: first eigenvalue, eigenvalue restart, or fixed source;
* energy-group structure and neutron-group count;
* scattering order used by the macroscopic cross sections;
* trusted angular quadrature;
* cross-section and restart logical units used by the local executable;
* physical boundaries and intended boundary conditions.

These values must agree across the mixture library, quadrature, and DORT
controls. The package can check internal consistency but cannot infer the
physics of your local library.

Step 2: define materials or mixtures
------------------------------------

For the local external-mixer workflow, load a mixture workbook into a fresh
model:

.. code-block:: python

   model = DORTModel("case_name")
   model.load_mixtures_from_excel(
       "mixtures.xlsx",
       legendre_order=5,
   )

Workbook order is significant. It fixes the natural material IDs and the
cross-section table sequence used by negative ``9$$`` references. Do not sort
or rename mixture columns after a model has been reviewed.

See :doc:`mixtures` for spreadsheet and programmatic alternatives.

Step 3: create the mesh around physical interfaces
--------------------------------------------------

Each axis can contain several uniform segments:

.. code-block:: python

   model.mesh.r.add_segment(0.0, 50.0, step=2.5)
   model.mesh.r.add_segment(50.0, 150.0, step=10.0)

   model.mesh.z.add_segment(-100.0, -50.0, step=10.0)
   model.mesh.z.add_segment(-50.0, 50.0, step=2.5)
   model.mesh.z.add_segment(50.0, 100.0, step=10.0)

Good practice:

* place mesh boundaries at important material interfaces;
* refine where flux or source gradients are expected;
* avoid unnecessary fine cells far from the response of interest;
* verify ``model.mesh.shape`` before generating large arrays;
* remember that internal arrays use ``(z, r) == (JM, IM)`` ordering.

Radial coordinates must be non-negative. Negative axial coordinates are
allowed.

Step 4: define background and regions
-------------------------------------

Use a background material to fill the whole mesh, then overwrite it with named
rectangular regions:

.. code-block:: python

   model.set_background("Sodium")

   model.add_region(
       "core",
       material="Fuel",
       r=(0.0, 50.0),
       z=(-50.0, 50.0),
       priority=20,
   )
   model.add_region(
       "control_rod",
       material="B4C",
       r=(0.0, 10.0),
       z=(-50.0, 50.0),
       priority=50,
   )

The second region overwrites the first only where their cell-centre masks
overlap.

Priority rules
~~~~~~~~~~~~~~

Use a deliberate priority scale, for example:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Priority range
     - Typical purpose
     - Meaning
   * - background
     - coolant or void
     - fills cells not selected by a region
   * - 10--29
     - large physical zones
     - core, pool, reflector, vessel
   * - 30--49
     - shields and structures
     - intentional overwrite of larger zones
   * - 50 and above
     - penetrations or inserts
     - small features that must win overlaps

The numerical ranges are a project convention, not a DORT requirement. What
matters is that the intent is obvious and documented. Equal-priority overlaps
raise an error.

Step 5: validate and build
--------------------------

.. code-block:: python

   warnings = model.validate(strict_region_bounds=True)
   summary = model.build(strict_region_bounds=True)

   print(warnings)
   print(summary)

``strict_region_bounds=True`` catches regions extending outside the mesh. The
normal build also checks material names, mesh completeness, scattering-order
consistency, and ambiguous overlaps.

Step 6: inspect the final ownership
-----------------------------------

Review numerical summaries and plots:

.. code-block:: python

   print(model.material_cell_counts())
   print(model.region_cell_counts())
   print(model.cell_assignment(z_index=10, r_index=5))

   save_material_plot(model, "materials.png", show_mesh=True)
   save_region_plot(model, "regions.png", show_mesh=True)
   save_material_region_union_plot(model, "material_region_union.png")
   write_outline_csv(model, "geometry_outlines.csv")

The material plot answers *what cross section does each cell use?* The region
plot answers *which definition won each overlap?* Both views are necessary.
The combined view fills each cell by material, draws every final region and
material boundary, and labels each connected region/material area with its
material name. A boundary remains between adjacent regions even if they use
the same material. ``geometry_outlines.csv`` provides separate material,
region, and union R/Z column pairs. In Origin or Excel, select each pair as
an XY line series; a blank row separates each segment so unrelated outlines
are not connected. Coordinates use the mesh units supplied to the model.

Step 7: write mixture-based zones and geometry
-----------------------------------------------

.. code-block:: python

   writer = DORTWriter(
       model,
       zone_policy="material",
       cross_section_unit=51,
   )

   print(writer.zone_table_text())
   print(writer.material_layout_text())
   writer.write_block4_fragment("geometry_material.inc")

The default ``"material"`` policy gives one ``9$$`` entry per used mixture and
sets ``IZM`` to that number. Choose ``"region"`` explicitly only when physical
regions must remain separate DORT zones; repeated materials then have repeated
``9$$`` entries. Compare ``writer.izm`` and the printed zone table with your
intended ``IZM``.

Step 8: add quadrature and run controls
---------------------------------------

Generate and validate the angular set, then create a run profile from the
writer. Geometry-derived values such as ``IM``, ``JM``, ``IZM``, and ``ISCTM``
are transferred automatically.

.. code-block:: python

   quadrature = generate_legacy_quadrature(order=8, symmetry="half")
   quadrature.write_dort("quadrature.inc")

   run = writer.create_run_control(
       "fixed_source",
       energy_groups=217,
       quadrature_directions=quadrature.direction_count,
       neutron_groups=175,
   )

Use :doc:`eigenvalue` or :doc:`fixed_source` for mode-specific steps.

Step 9: generate the combined input
-----------------------------------

Review the separate fragments, then supply the group-wise 1** values and
write the combined input. For example, with 217 groups:

.. code-block:: python

   group_values = [0.0] * 217  # Replace with your reviewed data.
   writer.write_complete_input(
       "dortinp.inp", run_control=run, quadrature=quadrature,
       array1=group_values, title="Reviewed case",
   )

The writer places 61$$/62$$/63**, the empty block, 82**/83**/81**/84$$,
1**/2**/4**/8$$/9$$, then the starting-flux and source cards required by the
run profile. It writes the ``t`` delimiters at the corresponding block ends.
Compare the resulting input with a known working case.

The final checks in :doc:`validation` should be treated as part of model
construction, not as an optional cleanup step.
