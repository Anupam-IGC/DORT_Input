Materials
=========

Materials are the names used by the geometry layer.  They receive natural IDs
``1, 2, 3, ...`` in registration order and carry the common Legendre scattering
order used by the model.

Two ways to define them
-----------------------

For geometry-only work, register a material directly:

.. code-block:: python

   model.add_material(
       "Steel",
       legendre_order=5,
       description="Structural shielding material",
   )

For the verified local external-mixture workflow, the more convenient route is
:meth:`model.DORTModel.add_mixture`.  It creates the geometry-facing material
and the external mixing recipe together:

.. code-block:: python

   model.add_mixture(
       "Mixture-1",
       {5125: 1.10597e-2, 5131: 8.27546e-3, 825: 2.90028e-2},
       legendre_order=5,
   )

The next material/mixture receives ID 2, then 3, and so on.

Common Legendre order
---------------------

DORT uses one global scattering order, so materials in a valid model must use
the same ``legendre_order``.  For P5, the external mixer writes six cross-section
tables per physical mixture.

.. important::

   The natural material ID is **not** the value written to local DORT ``9$$``
   when external mixtures are used.  The ``9$$`` reference is derived from the
   first table occupied by that mixture in ``mixf.cr``.

Inspecting the registry
-----------------------

.. code-block:: python

   print(model.materials.names)
   print(model.materials.ids)
   print(model.materials["Mixture-1"])

See :doc:`mixtures` for cross-section packing and :doc:`dort_mapping` for the
DORT array mapping.
