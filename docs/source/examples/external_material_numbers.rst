Explicit 9$ Material-Number Overrides
=====================================

Normally external-mixture materials obtain their negative 9$ references
automatically.

For a material that is not produced by the registered external mixture file,
an explicit advanced mapping may be supplied:

.. code-block:: python

   writer = DORTWriter(
       model,
       material_numbers={"Special": -25},
   )

Zero is not allowed. Do not override a material that already has a registered
external mixture recipe, because its table reference is calculated from the
mixture sequence and Legendre order.
