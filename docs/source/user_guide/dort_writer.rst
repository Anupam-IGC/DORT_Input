DORT Writer
===========

:class:`writer.DORTWriter` is the bridge between the built physical model and
DORT/FIDO input fragments.  Create it only after ``model.build()``.

.. code-block:: python

   writer = DORTWriter(
       model,
       zone_policy="region",
       cross_section_unit=51,
       cross_section_filename="mixf.cr",
   )

Zone policy
-----------

``zone_policy="region"``
   Preserve final geometric-owner identity.  Two regions using the same
   material can remain separate DORT zones.

``zone_policy="material"``
   Collapse all cells using the same material into one DORT zone.

For shielding models, ``region`` is usually more informative during inspection
and editing.

Generated geometry/material cards
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Card
     - Meaning
   * - ``2*``
     - Z fine-mesh boundaries
   * - ``4*``
     - R fine-mesh boundaries
   * - ``8$``
     - material-zone number for every fine-mesh cell
   * - ``9$``
     - local cross-section reference for each material zone
   * - ``84$``
     - optional edit-region mapping helper

For external P5 mixtures, typical ``9$$`` values are ``-1, -7, -13, ...``.

Useful inspection methods
-------------------------

.. code-block:: python

   print(writer.summary_text())
   print(writer.zone_table_text())
   print(writer.material_layout_text())

These are recommended before writing a production fragment.

Write Block 4 fragments
-----------------------

.. code-block:: python

   writer.write_block4_fragment("geometry_material.inc")

The default fragment contains ``2*``, ``4*``, ``8$``, and ``9$``.  It does not
pretend to finish every remaining Block-4 card.

Cross-section file unit
-----------------------

The local sample reads ``mixf.cr`` on logical unit 51.  The writer exposes this
through ``required_file_units`` and the run-control builder uses it as
``NTSIG``.

.. code-block:: python

   print(writer.required_file_units)
   print(writer.array61())

Run and source builders
-----------------------

The writer also provides convenient entry points without mixing their logic
into geometry serialization:

.. code-block:: python

   run = writer.create_run_control(
       "eigenvalue_first",
       energy_groups=217,
       quadrature_directions=48,
   )

   source = writer.create_source(background=1.0e-20)

See :doc:`run_control` and :doc:`fixed_source`.
