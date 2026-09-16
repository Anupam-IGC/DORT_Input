Comprehensive Eigenvalue Rerun Workflow
=======================================

Configure the restart calculation and prepare the unit-21 flux output as the unit-20 guess for the next run.

What this example demonstrates
------------------------------

* eigenvalue_rerun preset;
* unit 20 / unit 21 restart convention;
* guessflux.bin preparation;
* run-control/card-policy inspection;
* geometry and quadrature fragments.

Run it
------

.. code-block:: bash

   python examples/comprehensive_eigenvalue_rerun.py

The script writes its generated fragments/plots under ``example_output/``.

Full script
-----------

.. literalinclude:: ../../../examples/comprehensive_eigenvalue_rerun.py
   :language: python
   :linenos:

.. note::

   Microscopic MAT numbers/densities and any generated group spectrum in these
   examples are demonstration inputs.  Replace them with validated problem data
   before a production calculation.
