DORT Array Mapping and Ordering
===============================

Internal array layout
---------------------

The internal zone/material maps use:

.. code-block:: text

   shape = (JM, IM) = (nz, nr)

For the DORT array ``IJZN(I,J)``:

.. code-block:: text

   I = R index
   J = Z index

Serialization order
-------------------

The writer serializes the zone map as:

.. code-block:: text

   J = 1: I = 1, 2, ..., IM
   J = 2: I = 1, 2, ..., IM
   ...

Thus the expanded DORT ``8$`` stream corresponds to:

.. code-block:: python

   writer.zone_map.ravel(order="C")

The expanded stream is available through:

.. code-block:: python

   stream = writer.ijzn_stream()

and must contain:

.. code-block:: python

   writer.im * writer.jm

entries.

Zone-to-material mapping
------------------------

The ``8$`` array contains zone numbers by fine-space cell. The ``9$`` array
maps each material zone to the DORT material number associated with that zone.

This is why a zone number should not be confused with a cross-section material
number.

Validation recommendation
-------------------------

When modifying writer logic, compare generated array lengths and ordering
against the DORT input echo/output for a known problem.
