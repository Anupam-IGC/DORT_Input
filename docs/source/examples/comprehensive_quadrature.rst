Comprehensive Quadrature Workflow
=================================

Compare the historical DOQDP-compatible family with the modern positive-weight product family.

What this example demonstrates
------------------------------

* legacy S8 generation;
* product quadrature;
* validation reports;
* 81*/82*/83* output;
* quadrature visualization.

Run it
------

.. code-block:: bash

   python examples/comprehensive_quadrature.py

The script writes its generated fragments/plots under ``example_output/``.

Full script
-----------

.. literalinclude:: ../../../examples/comprehensive_quadrature.py
   :language: python
   :linenos:

.. note::

   Microscopic MAT numbers/densities and any generated group spectrum in these
   examples are demonstration inputs.  Replace them with validated problem data
   before a production calculation.
