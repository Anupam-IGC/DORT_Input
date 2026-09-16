Spreadsheet-Driven Mixture Preparation
======================================

The local workflow prepares macroscopic cross sections **outside DORT**.  The
recommended user interface is now an Excel workbook matching the layout used by
the supplied ``mixture.py`` script.

.. container:: workflow-box

   ``mixtures.xlsx`` → ``mix.inp`` → ``m_ia_oa.for`` → ``mixf.cr`` →
   logical unit 51 (``NTSIG``) → modified DORT

The API does not generate stock DORT ``10$$/11$$/12*`` in-core mixing cards.

Workbook layout
---------------

The default worksheet is named ``Read``.  The first two columns are fixed:

* ``Nuclide`` — readable isotope/element label used for inspection;
* ``MAT No.`` — microscopic material number in the source cross-section library.

Every column after ``MAT No.`` defines one final macroscopic mixture.  A blank
cell means that microscopic material is absent; a nonblank cell is the atom
density used by the external mixer.

A simplified example is:

.. list-table::
   :header-rows: 1
   :widths: 18 14 18 18 18

   * - Nuclide
     - MAT No.
     - Sodium
     - B4C Powder
     - Carbon Steel
   * - Na
     - 1125
     - 2.22552E-02
     -
     -
   * - C
     - 600
     -
     - 1.92224E-02
     - 8.60572E-04
   * - B10
     - 525
     -
     - 1.50704E-02
     -
   * - Fe
     - 2600
     -
     -
     - 8.18672E-02

The **left-to-right mixture-column order is significant**.  It becomes mixture
ID ``1, 2, 3, ...`` and therefore determines the local negative ``9$$``
references.

Recommended Python workflow
---------------------------

Load the workbook and generate the three preparation files in one call:

.. code-block:: python

   from model import DORTModel

   model = DORTModel("shield_model")

   files = model.prepare_mixtures_from_excel(
       "mixtures.xlsx",
       sheet_name="Read",
       legendre_order=5,
       output_dir="mixture_output",
   )

   print(model.mixtures.layout_text(5))
   print(files)

This registers every mixture as a model material and writes:

.. code-block:: text

   mixture_output/
   ├── mix.inp
   ├── Mixture_Names.txt
   └── dort_mix_cards.txt

After import, the workbook column names are normal geometry material names:

.. code-block:: python

   model.set_background("Sodium")

   model.add_region(
       "steel_shield",
       material="Carbon Steel",
       r=(50.0, 80.0),
       z=(-40.0, 40.0),
       priority=20,
   )

Generated ``mix.inp``
---------------------

For P5, the supplied example workbook contains six mixtures.  The generated
file begins:

.. code-block:: text

   5
   6
   1 1125
   2.22552E-02
   1 1837
   2.67979E-05
   ...

The format intentionally follows the standalone spreadsheet script:

#. Legendre order;
#. number of mixtures;
#. number of components followed by microscopic MAT numbers;
#. corresponding atom densities;
#. repeat the last two lines for every mixture.

``Mixture_Names.txt``
---------------------

The API also preserves the convenient mixture-number lookup file:

.. code-block:: text

   Mixture Number    Mixture Name
   1                 Sodium
   2                 Argon
   3                 Graphite
   4                 Lead
   5                 B4C Powder
   6                 Carbon Steel

Cross-section table numbering
-----------------------------

For scattering order ``L``, each physical mixture occupies ``L+1`` consecutive
records in ``mixf.cr``.  For mixture ID ``m``:

.. math::

   t_m = 1 + (m-1)(L+1)

and the locally modified DORT uses ``-t_m`` as the material reference.

For the supplied six-mixture P5 workbook:

.. list-table::
   :header-rows: 1
   :widths: 12 26 24 18

   * - ID
     - Mixture
     - ``mixf.cr`` tables
     - local ``9$$``
   * - 1
     - Sodium
     - 1 .. 6
     - -1
   * - 2
     - Argon
     - 7 .. 12
     - -7
   * - 3
     - Graphite
     - 13 .. 18
     - -13
   * - 4
     - Lead
     - 19 .. 24
     - -19
   * - 5
     - B4C Powder
     - 25 .. 30
     - -25
   * - 6
     - Carbon Steel
     - 31 .. 36
     - -31

Compact mixture cards versus zone-aware cards
---------------------------------------------

``model.prepare_mixtures_from_excel(...)`` writes the same compact mapping used
by the standalone script:

.. code-block:: text

   84$$ 1 2 3 4 5 6 t
   9$$ -1 -7 -13 -19 -25 -31 t

This compact form assumes **one DORT zone per mixture/material**.

If the geometry writer uses ``zone_policy="region"``, several geometric zones
may share one physical mixture.  In that case generate the final deck cards
from the writer instead:

.. code-block:: python

   from writer import DORTWriter

   writer = DORTWriter(model, zone_policy="region")
   print(writer.array84_by_material())
   print(writer.array9())

   writer.write_mixture_cards("dort_mix_cards_zone_aware.txt")

The writer repeats the appropriate mixture ID and negative cross-section
reference for every generated DORT zone.

Command-line workflow
---------------------

The top-level ``mixture.py`` script is now an API-backed command-line front end.
The old defaults are preserved:

.. code-block:: bash

   python mixture.py mixtures.xlsx

Equivalent explicit use is:

.. code-block:: bash

   python mixture.py mixtures.xlsx \
       --sheet Read \
       --order 5 \
       --output-dir mixture_output

If ``mixf.cr`` has already been generated, it can also be checked:

.. code-block:: bash

   python mixture.py mixtures.xlsx \
       --order 5 \
       --validate mixf.cr

Programmatic mixture definitions
--------------------------------

Direct Python definitions remain available when a spreadsheet is inconvenient:

.. code-block:: python

   model.add_mixture(
       "Sodium",
       {1125: 2.22552e-2},
       legendre_order=5,
   )

   model.add_mixture(
       "B4C Powder",
       {
           600: 1.92224e-2,
           525: 1.50704e-2,
           528: 6.18192e-2,
       },
   )

For routine work, the spreadsheet path is preferred because it keeps mixture
composition, MAT numbers, readable nuclide names, and mixture order visible in
one place.

Validation
----------

Spreadsheet import checks for:

* required ``Nuclide`` and ``MAT No.`` columns;
* unique, non-empty mixture column names;
* positive integer MAT numbers;
* finite, non-negative atom densities;
* duplicate MAT numbers within one mixture;
* empty mixture columns;
* external-mixer limits on mixture/component counts.

The generated ``mixf.cr`` can still be validated with:

.. code-block:: python

   check = model.validate_mixture_file("mixf.cr")
   print(check.summary_text())

For P5 with six mixtures the validator expects 36 sequential tables.

Dependencies
------------

Spreadsheet import uses ``pandas`` with ``openpyxl``.  Both are included in the
updated project ``requirements.txt``.

.. seealso::

   * :doc:`../examples/comprehensive_mixture_spreadsheet`
   * :doc:`dort_writer`
   * :doc:`dort_mapping`
