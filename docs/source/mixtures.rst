Mixtures and Cross-Section Mapping
==================================

The verified local workflow prepares macroscopic mixtures outside DORT:

.. code-block:: text

   reviewed workbook
          |
          v
      mix.inp
          |
          v
   external m_ia_oa.for mixer + microscopic library
          |
          v
      mixf.cr
          |
          v
   modified DORT reads NTSIG (normally unit 51)

The Python package prepares and validates the bookkeeping around this process;
it does not execute the mixer or manufacture nuclear data.

Workbook format
---------------

The worksheet must contain:

* ``Nuclide``: a readable label used for review;
* ``MAT No.``: the microscopic-library identifier;
* one subsequent column for each final mixture;
* atom density in every nuclide row belonging to that mixture;
* blank cells where a nuclide is absent.

For example:

.. list-table::
   :header-rows: 1

   * - Nuclide
     - MAT No.
     - Sodium
     - Carbon Steel
   * - Na
     - 1125
     - 2.22552E-2
     -
   * - Fe
     - 2600
     -
     - 8.18667E-2
   * - Cr
     - 2400
     -
     - 1.80650E-4

Mixture-column order is part of the input definition. It controls mixture IDs,
``mixf.cr`` table ranges, and negative DORT material references.

Recommended Python workflow
---------------------------

.. code-block:: python

   from dort_input import DORTModel

   model = DORTModel("case_name")
   model.load_mixtures_from_excel(
       "mixtures.xlsx",
       legendre_order=5,
   )

The first worksheet is used by default, whatever its name. Use
``sheet_name="Other"`` only when selecting a different worksheet.

Load mixtures before setting the background or adding regions. Workbook column
names become the material names used by geometry:

.. code-block:: python

   model.set_background("Sodium")
   model.add_region(
       "vessel",
       material="Carbon Steel",
       r=(40.0, 50.0),
       z=(-60.0, 60.0),
       priority=30,
   )

Write all preparation files together:

.. code-block:: python

   files = model.write_mixture_preparation_files("mixture_output")

This produces:

``mix.inp``
   Scattering order, mixture count, MAT numbers, and atom densities for the
   external mixer.

``Mixture_Names.txt``
   Human-readable mixture-number mapping for checking and records.

``dort_mix_cards.txt``
   Compact ``84$$``/``9$$`` mapping for one zone per
   mixture. A normal region-zone model should use the writer's zone-aware cards
   instead.

Table numbering and negative ``9$$`` references
------------------------------------------------

For scattering order :math:`L`, each mixture occupies :math:`L+1` sequential
tables. Mixture :math:`m` starts at:

.. math::

   n_{\mathrm{first}} = 1 + (m-1)(L+1).

The local modified-DORT ``9$$`` reference is the negative of this first table
number. For P5:

.. list-table::
   :header-rows: 1

   * - Mixture ID
     - Tables
     - ``9$$`` value
   * - 1
     - 1--6
     - -1
   * - 2
     - 7--12
     - -7
   * - 3
     - 13--18
     - -13

Always inspect the calculated mapping:

.. code-block:: python

   writer = DORTWriter(model, zone_policy="material", cross_section_unit=51)
   print(writer.material_layout_text())
   print(writer.zone_table_text())

Command-line preparation
------------------------

The same spreadsheet workflow is available without writing a model script:

.. code-block:: bash

   dort-mixture mixtures.xlsx \
       --order 5 \
       --output-dir mixture_output

Pass ``--sheet Other`` to select a worksheet other than the first one.

If ``mixf.cr`` already exists, request a consistency check:

.. code-block:: bash

   dort-mixture mixtures.xlsx --order 5 --validate mixf.cr

Programmatic alternative
------------------------

Mixtures may be defined directly when a spreadsheet is inconvenient:

.. code-block:: python

   model.add_mixture(
       "Sodium",
       {1125: 2.22552e-2},
       legendre_order=5,
   )
   model.add_mixture(
       "B4C Powder",
       {600: 1.92224e-2, 525: 1.50704e-2, 528: 6.18192e-2},
   )

Use only values verified against the microscopic library used by the external
mixer.

Review checklist
----------------

Before accepting ``mixf.cr``:

* confirm every mixture column name and order;
* confirm MAT numbers against the intended microscopic library;
* check density units and numerical values independently;
* confirm one common Legendre order for all materials;
* verify the expected table count, ``n_mixtures * (L + 1)``;
* compare the writer's table ranges and negative ``9$$`` values;
* confirm DORT ``NTSIG`` points to the actual ``mixf.cr`` file unit.
