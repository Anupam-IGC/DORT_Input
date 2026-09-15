DORT Writer
===========

Create a writer only after the model has been built:

.. code-block:: python

   from writer import DORTWriter

   model.build()
   writer = DORTWriter(model)

Creating a writer before ``model.build()`` raises an error.

Zone policies
-------------

DORT distinguishes a material **zone** from the material number assigned to
that zone.

``zone_policy="region"``
~~~~~~~~~~~~~~~~~~~~~~~~

This is the recommended policy for shielding models.

.. code-block:: python

   writer = DORTWriter(
       model,
       zone_policy="region",
   )

Each final geometric owner gets a separate DORT zone. Different regions may
therefore use the same physical material while retaining separate zone
identities.

Example:

.. code-block:: text

   Zone 1 -> background -> Sodium
   Zone 2 -> core       -> Core
   Zone 3 -> shield     -> SS316
   Zone 4 -> vessel     -> SS316

``zone_policy="material"``
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   writer = DORTWriter(
       model,
       zone_policy="material",
   )

All cells containing the same material share one zone. This reduces ``IZM``
but loses geometric-region identity.

Generated arrays
----------------

The writer currently generates:

.. code-block:: text

   2*   Z fine-mesh boundaries
   4*   R fine-mesh boundaries
   8$   material zone by fine-space cell
   9$   material number by material zone

It can additionally generate:

.. code-block:: text

   84$  edit region by material zone

using an identity edit-region mapping.

Generate individual arrays with:

.. code-block:: python

   print(writer.array2())
   print(writer.array4())
   print(writer.array8())
   print(writer.array9())
   print(writer.array84_identity())

The ``8$`` writer uses FIDO repetition operators:

* ``R`` for repeated values within a row,
* ``Q`` for repeated complete radial rows.

Control values
--------------

The writer reports values that must be consistent with DORT ``62$``:

.. code-block:: python

   writer.required_control_values

Typical entries include:

.. code-block:: text

   IZM
   IM
   JM
   INGEOM

Inspect the complete writer summary with:

.. code-block:: python

   print(writer.summary_text())

Writing a Block-4 fragment
--------------------------

Generate ``2*``, ``4*``, ``8$``, and ``9$``:

.. code-block:: python

   writer.write_block4_fragment(
       "geometry_material_fragment.inp"
   )

No terminating ``T`` is written by default because a real Block 4 may contain
additional arrays.

When these are genuinely the final arrays in the block:

.. code-block:: python

   writer.write_block4_fragment(
       "geometry_material_fragment.inp",
       terminate_block=True,
   )

To regenerate only material filling when the DORT deck already has the mesh
arrays:

.. code-block:: python

   writer.write_block4_fragment(
       "material_only.inp",
       include_mesh=False,
   )

This writes only ``8$`` and ``9$``.
