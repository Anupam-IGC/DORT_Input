Comprehensive Fixed-Source Workflow
===================================

Build a mesh-aligned source from existing regions and mesh coordinates, read the energy dependence from a separate file, and generate 96**/98**.

What this example demonstrates
------------------------------

* source by region;
* overlapping source contributions;
* source by mesh coordinates;
* file-based 217-group spectrum;
* fixed_source preset;
* 96** + 98** serialization;
* spatial-source visualization.

Run it
------

.. code-block:: bash

   python examples/comprehensive_fixed_source.py

The script writes its generated fragments/plots under ``example_output/``.

Full script
-----------

.. literalinclude:: ../../../examples/comprehensive_fixed_source.py
   :language: python
   :linenos:

.. note::

   Microscopic MAT numbers/densities and any generated group spectrum in these
   examples are demonstration inputs.  Replace them with validated problem data
   before a production calculation.
