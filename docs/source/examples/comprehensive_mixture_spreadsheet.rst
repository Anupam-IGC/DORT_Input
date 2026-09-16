Spreadsheet Mixture Workflow
============================

This example starts from the supplied spreadsheet-style mixture table, writes
all external-mixer preparation files, then immediately uses the imported
mixture names in an R-Z geometry.

It also demonstrates the difference between the compact ``84$$/9$$`` cards
written during mixture preparation and the zone-aware cards produced by a
``DORTWriter`` using ``zone_policy="region"``.

Run from the repository root:

.. code-block:: bash

   python examples/comprehensive_mixture_spreadsheet.py

Source
------

.. literalinclude:: ../../../examples/comprehensive_mixture_spreadsheet.py
   :language: python
   :linenos:
