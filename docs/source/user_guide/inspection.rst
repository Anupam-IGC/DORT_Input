Inspecting the Built Model
==========================

Main result arrays
------------------

After a successful build, the principal arrays are:

.. code-block:: python

   model.material_id_map
   model.material_name_map
   model.region_map
   model.priority_map

Each array has shape:

.. code-block:: text

   (nz, nr)

Material maps
-------------

``material_id_map`` stores the internal material IDs:

.. code-block:: python

   ids = model.material_id_map

``material_name_map`` stores readable material names:

.. code-block:: python

   names = model.material_name_map

Region ownership
----------------

``region_map`` stores the final region that owns each cell:

.. code-block:: python

   owners = model.region_map

Background cells use the owner name ``background``.

``priority_map`` records the priority responsible for the final cell
assignment.

Inspecting one cell
-------------------

Use ``cell_assignment`` when a plotted cell does not have the expected
material:

.. code-block:: python

   info = model.cell_assignment(
       z_index=10,
       r_index=15,
   )

A typical result contains the cell indices, cell-centre coordinates, material
ID/name, owning region, and priority.

Cell-count summaries
--------------------

Count final cells by material:

.. code-block:: python

   model.material_cell_counts()

Count final ownership by region:

.. code-block:: python

   model.region_cell_counts()

A lower-priority region may own fewer cells than its original geometric mask
because a higher-priority region can overwrite part of it.
