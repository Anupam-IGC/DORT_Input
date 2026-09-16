Comprehensive First-Eigenvalue Workflow
=======================================

Prepare external mixtures, geometry, a legacy S8 quadrature, and human-readable first-run controls.

What this example demonstrates
------------------------------

* mix.inp generation;
* mixf.cr validation hook;
* negative local 9$$ references;
* legacy S8 quadrature;
* eigenvalue_first preset;
* readable run settings and card policy.

Run it
------

.. code-block:: bash

   python examples/comprehensive_eigenvalue_first.py

The script writes its generated fragments/plots under ``example_output/``.

Full script
-----------

.. literalinclude:: ../../../examples/comprehensive_eigenvalue_first.py
   :language: python
   :linenos:

.. note::

   Microscopic MAT numbers/densities and any generated group spectrum in these
   examples are demonstration inputs.  Replace them with validated problem data
   before a production calculation.
