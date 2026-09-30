DORT Input Preparation
======================

This package helps you turn a readable R-Z physical model into validated DORT
input and process the VARFLM flux output. It keeps mesh construction,
materials, regions, quadrature, run controls, fixed sources, and response
fields in Python for review.

Start here
----------

If this is your first model, follow these steps in order:

1. :doc:`Install the package <installation>`.
2. Work through :doc:`quickstart` and run ``examples/modeling_basics.py``.
3. Adapt the model using :doc:`modeling_workflow`.
4. Choose either :doc:`eigenvalue` or :doc:`fixed_source`.
5. Complete the :doc:`validation` before submitting a DORT calculation.
6. Use :doc:`output_processing` to inspect fluxes and compute response fields.

The first tutorial can be run immediately:

.. code-block:: bash

   python examples/modeling_basics.py

It creates mixture-preparation files, geometry/material cards, inspection
tables, and two plots under ``example_output/01_modeling_basics``.

Learning path
-------------

.. list-table::
   :header-rows: 1
   :widths: 28 42 30

   * - Page
     - What you learn
     - Use it when
   * - :doc:`quickstart`
     - The shortest complete model-building sequence
     - starting your first model
   * - :doc:`modeling_workflow`
     - Mesh, mixtures, regions, priorities, inspection, and writing
     - adapting geometry safely
   * - :doc:`mixtures`
     - Spreadsheet layout and the external ``mix.inp -> mixf.cr`` workflow
     - preparing cross sections
   * - :doc:`eigenvalue`
     - First-run and restart calculation profiles
     - preparing criticality inputs
   * - :doc:`fixed_source`
     - Spatial and groupwise source construction
     - preparing shielding inputs
   * - :doc:`quadrature_sets`
     - Directional concentration and first-octant sphere plots
     - selecting angular resolution
   * - :doc:`validation`
     - A pre-run checklist and common-error guide
     - reviewing a production case
   * - :doc:`output_processing`
     - Read VARFLM, integrate groups, compute dose, and plot R-Z fields
     - after a DORT run
   * - :doc:`conventions`
     - Local DORT conventions and package boundaries
     - interpreting generated cards
   * - :doc:`examples`
     - Runnable modeling and post-processing tutorials
     - learning by modifying working scripts

What the package generates
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Output
     - Purpose
   * - ``mix.inp`` and mapping files
     - Input and bookkeeping for the external macroscopic mixer
   * - ``2**``, ``4**``, ``8$$``, ``9$$``
     - R-Z boundaries, zone map, and local material references
   * - ``81**``, ``82**``, ``83**``
     - Angular quadrature arrays
   * - ``61$$``, ``62$$``, ``63**``
     - File units and readable run controls
   * - ``96**`` and ``98**``
     - Mesh-based fixed-source spatial and energy fields

The package intentionally writes **fragments**, not an unchecked universal
deck. First-run ``93**``--``95**`` cards use a uniform 1.0 default. Review
site-specific cards against a trusted local template. See
:doc:`conventions` for the exact boundary of responsibility.

.. toctree::
   :hidden:
   :maxdepth: 2

   installation
   quickstart
   modeling_workflow
   mixtures
   eigenvalue
   fixed_source
   quadrature_sets
   validation
   output_processing
   conventions
   examples
   api/index
