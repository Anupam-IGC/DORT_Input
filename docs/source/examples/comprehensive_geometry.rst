Comprehensive Geometry and Zone Workflow
========================================

Build and inspect a piecewise R-Z model, resolve region priorities, plot final maps, and serialize DORT geometry/material arrays.

What this example demonstrates
------------------------------

* piecewise R/Z mesh;
* material registration;
* region priorities and overlaps;
* material/region plotting;
* region-based DORT zones;
* 2*/4*/8*/9* and 84* output.

Run it
------

.. code-block:: bash

   python examples/comprehensive_geometry.py

The script writes its generated fragments/plots under ``example_output/``.

Full script
-----------

.. literalinclude:: ../../../examples/comprehensive_geometry.py
   :language: python
   :linenos:

.. note::

   Microscopic MAT numbers/densities and any generated group spectrum in these
   examples are demonstration inputs.  Replace them with validated problem data
   before a production calculation.
