Building and Validating a Model
===============================

After defining the mesh, materials, background, and regions, build the model:

.. code-block:: python

   summary = model.build()

The build stage performs the main consistency checks and generates the final
cell maps.

Build operations
----------------

The build process:

#. validates the mesh,
#. validates materials,
#. validates region references,
#. checks region/mesh intersections,
#. checks equal-priority overlaps,
#. fills the background,
#. applies regions from lower to higher priority,
#. checks for unfilled cells,
#. stores the final maps.

The returned object is a ``BuildSummary``:

.. code-block:: python

   print(summary)

Strict region bounds
--------------------

By default, a region that extends partly outside the model domain generates a
warning.

Use:

.. code-block:: python

   model.build(strict_region_bounds=True)

to treat such a case as an error.

Unfilled cells
--------------

Without a background material, every cell must be covered by an explicit
region. Unfilled cells normally cause ``model.build()`` to fail.

For temporary debugging only:

.. code-block:: python

   model.build(allow_unfilled=True)
