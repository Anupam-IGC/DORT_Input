Quick Start
===========

This page shows the shortest path from a physical R-Z model to useful DORT
input fragments.  For fuller scripts, go directly to :doc:`examples/index`.

1. Create the model and load mixtures
-------------------------------------

For routine calculations, start from the standard mixture workbook:

.. code-block:: python

   from model import DORTModel

   model = DORTModel("demo")

   model.prepare_mixtures_from_excel(
       "mixtures.xlsx",
       sheet_name="Read",
       legendre_order=5,
       output_dir="mixture_output",
   )

The workbook contains ``Nuclide`` and ``MAT No.`` followed by one column per
mixture.  This one call registers the mixture columns as model materials and
writes ``mix.inp``, ``Mixture_Names.txt``, and ``dort_mix_cards.txt``.

``mix.inp`` is consumed by the external ``m_ia_oa.for`` program, which creates
``mixf.cr``.  See :doc:`user_guide/mixtures` for the workbook format.

2. Define R-Z geometry
----------------------

.. code-block:: python

   model.mesh.r.add_segment(0.0, 80.0, step=5.0)
   model.mesh.r.add_segment(80.0, 120.0, step=2.0)
   model.mesh.z.add_segment(-80.0, -40.0, step=5.0)
   model.mesh.z.add_segment(-40.0, 40.0, step=2.0)
   model.mesh.z.add_segment(40.0, 80.0, step=5.0)

   model.set_background("Sodium")

   model.add_region(
       "central_region",
       material="Graphite",
       r=(0.0, 80.0),
       z=(-40.0, 40.0),
       priority=20,
   )
   model.add_region(
       "radial_shield",
       material="Carbon Steel",
       r=(80.0, 120.0),
       z=(-50.0, 50.0),
       priority=30,
   )

   summary = model.build()
   print(summary)

3. Create the DORT writer
-------------------------

.. code-block:: python

   from writer import DORTWriter

   writer = DORTWriter(
       model,
       zone_policy="region",
       cross_section_unit=51,
       cross_section_filename="mixf.cr",
   )

   print(writer.summary_text())
   writer.write_block4_fragment("geometry_material.inc")

For the supplied P5 workbook, the generated mixture references are ``-1, -7, -13, -19, -25, -31`` in workbook-column order.

4. Choose the run mode using readable settings
----------------------------------------------

.. code-block:: python

   run = writer.create_run_control(
       "eigenvalue_first",
       energy_groups=217,
       quadrature_directions=48,
       neutron_groups=175,
       maximum_outer_iterations=20,
       left_boundary="reflected",
       right_boundary="void",
       flux_extrapolation="theta_weighted",
   )

   print(run.settings_help())
   print(run.control_fragment())

Use ``"eigenvalue_rerun"`` for a restart from unit-20 ``guessflux.bin`` or
``"fixed_source"`` for a fixed-source calculation.

5. Optional: define a fixed source from the built model
-------------------------------------------------------

.. code-block:: python

   source = writer.create_source(background=1.0e-20)
   source.by_region("central_region", strength=1.0)
   source.set_energy_spectrum_file("source_spectrum.txt")

   fixed = writer.create_run_control(
       "fixed_source",
       energy_groups=217,
       quadrature_directions=48,
   )
   fixed.attach_source(source)

   print(fixed.source_fragment())

The API generates ``96**`` from the existing R-Z model and ``98**`` from the
spectrum file.

Next steps
----------

.. container:: doc-grid

   .. container:: doc-card

      **Geometry and plotting**

      :doc:`user_guide/mesh` · :doc:`user_guide/regions` ·
      :doc:`user_guide/plotting`

   .. container:: doc-card

      **Mixtures and DORT mapping**

      :doc:`user_guide/mixtures` · :doc:`user_guide/dort_mapping`

   .. container:: doc-card

      **Run modes**

      :doc:`user_guide/run_control`

   .. container:: doc-card

      **Fixed source**

      :doc:`user_guide/fixed_source`
