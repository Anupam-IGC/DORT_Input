Progressive Examples
====================

The examples form one learning sequence and share a single reviewed teaching
geometry. Run them from the repository root after installation.

.. list-table::
   :header-rows: 1
   :widths: 7 29 37 27

   * - Step
     - Script
     - Main features
     - Output directory
   * - 1
     - ``modeling_basics.py``
     - workbook mixtures, segmented mesh, priorities, strict build, cell/table/zone inspection, plots
     - ``01_modeling_basics``
   * - 2
     - ``eigenvalue_input.py``
     - legacy S8 quadrature, readable first-run settings, uniform ``93**``--``95**`` guess
     - ``02_eigenvalue_input``
   * - 3
     - ``fixed_source_input.py``
     - region/material/mesh selectors, combination rules, 217-group spectrum, ``96**``/``98**``
     - ``03_fixed_source_input``
   * - 4
     - ``eigenvalue_restart.py``
     - restart controls, file units, optional-card policy, flux-file preparation
     - ``04_eigenvalue_restart``
   * - 5
     - ``quadrature_comparison.py``
     - legacy, product, and +z-biased quadrature validation, serialization, first-octant 3-D plots
     - ``05_quadrature_comparison``

Run the sequence
----------------

.. code-block:: bash

   python examples/modeling_basics.py
   python examples/eigenvalue_input.py
   python examples/fixed_source_input.py
   python examples/eigenvalue_restart.py
   python examples/quadrature_comparison.py

All generated files are placed under ``example_output/``. The scripts do not
modify the supplied workbook or assemble an unchecked full DORT deck.

How to learn from them
----------------------

Start by reading ``modeling_basics.py`` from top to bottom. Its
``build_sample_model()`` function is reused by the other tutorials so that a
run-control change is not confused with a geometry change.

When adapting it to a real case, change one layer at a time:

#. replace the workbook and review mixture ordering;
#. change mesh boundaries and confirm the resulting ``IM``/``JM``;
#. add regions and review both plots and cell counts;
#. select a zone policy and inspect every row of the zone table;
#. choose the calculation profile and quadrature;
#. add the physically reviewed source or starting-flux data;
#. assemble and validate the complete deck.

Teaching-data warning
---------------------

The workbook combines convenient shielding materials, the fixed-source
spectrum is synthetic, and the product quadrature is included for comparison.
They demonstrate API behavior only. They do not constitute a criticality or
shielding benchmark and must not be treated as production physics input.

Where to go next
----------------

* Follow :doc:`quickstart` while editing the first example.
* Use :doc:`mixtures` before replacing the workbook.
* Read :doc:`eigenvalue` or :doc:`fixed_source` for mode-specific decisions.
* Complete :doc:`validation` before submitting a solver calculation.
* Use the :doc:`api/index` only when you need exact method signatures.
