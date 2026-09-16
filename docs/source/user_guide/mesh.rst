Mesh Definition
===============

The R-Z mesh is defined through ``model.mesh.r`` and ``model.mesh.z``. Each axis
is represented by a ``MeshAxis``.

Piecewise-uniform segments
--------------------------

.. code-block:: python

   model.mesh.r.add_segment(0.0, 100.0, step=2.0)
   model.mesh.r.add_segment(100.0, 140.0, step=1.0)

Adjacent segments must be continuous. A segment may alternatively be specified
with ``n_cells`` instead of ``step``.

Explicit boundaries
-------------------

.. code-block:: python

   model.mesh.r.add_edges([0.0, 1.0, 2.0, 5.0, 10.0, 20.0])

Explicit boundaries must be strictly increasing.

R and Z sign convention
-----------------------

For cylindrical R-Z geometry, the radial coordinate must be non-negative:

.. code-block:: text

   R >= 0

The axial coordinate Z is not restricted to positive values. Negative, zero,
and positive Z values may be used, for example when ``Z=0`` is chosen at the
core mid-plane:

.. code-block:: python

   model.mesh.z.add_segment(-100.0, -50.0, step=5.0)
   model.mesh.z.add_segment(-50.0,  50.0, step=2.0)
   model.mesh.z.add_segment( 50.0, 100.0, step=5.0)

Useful properties
-----------------

.. code-block:: python

   model.mesh.r.edges
   model.mesh.r.centers
   model.mesh.r.widths
   model.mesh.r.n_cells
   model.mesh.z.edges
   model.mesh.z.centers
   model.mesh.shape
   model.mesh.n_cells

Array convention
----------------

All internal 2-D maps use ``shape = (nz, nr)`` and are indexed as
``array[z_index, r_index]``. The DORT writer uses the same convention internally.
