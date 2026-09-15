Mesh Definition
===============

The R-Z mesh is defined through two axes:

.. code-block:: python

   model.mesh.r
   model.mesh.z

Each axis is represented by a ``MeshAxis``.

Piecewise-uniform segments
--------------------------

A uniform segment can be specified by its interval and cell width:

.. code-block:: python

   model.mesh.r.add_segment(
       start=0.0,
       end=100.0,
       step=2.0,
   )

This produces boundaries:

.. code-block:: text

   0, 2, 4, 6, ..., 100

Segments may be appended:

.. code-block:: python

   model.mesh.r.add_segment(100.0, 140.0, step=1.0)
   model.mesh.r.add_segment(140.0, 300.0, step=5.0)

Adjacent segments must be continuous. For example, the following is invalid:

.. code-block:: python

   model.mesh.r.add_segment(0.0, 100.0, step=5.0)
   model.mesh.r.add_segment(110.0, 200.0, step=5.0)

The second segment must begin at ``100.0``.

Segment by number of cells
--------------------------

Instead of a cell width, specify ``n_cells``:

.. code-block:: python

   model.mesh.r.add_segment(
       0.0,
       100.0,
       n_cells=50,
   )

Specify either ``step`` or ``n_cells``, not both.

Explicit mesh boundaries
------------------------

For an irregular mesh:

.. code-block:: python

   model.mesh.r.add_edges(
       [0.0, 1.0, 2.0, 5.0, 10.0, 20.0]
   )

Explicit boundaries must be strictly increasing.

Useful properties
-----------------

.. code-block:: python

   model.mesh.r.edges
   model.mesh.r.centers
   model.mesh.r.widths
   model.mesh.r.n_cells
   model.mesh.r.bounds

   model.mesh.z.edges
   model.mesh.z.centers

   model.mesh.shape
   model.mesh.n_cells

Array convention
----------------

All internal 2-D maps use:

.. code-block:: text

   shape = (nz, nr)

and are indexed as:

.. code-block:: python

   array[z_index, r_index]

This convention is also used by the DORT writer.
