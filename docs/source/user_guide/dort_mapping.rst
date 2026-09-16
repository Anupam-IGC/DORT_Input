DORT Mapping and Local Conventions
==================================

This page is the compact reference for how the Python model is serialized into
the locally modified DORT input convention.

Array ordering
--------------

Internal two-dimensional maps use:

.. code-block:: text

   shape = (JM, IM) = (nz, nr)
   map[z_index, r_index]

When serialized to DORT, the radial ``I`` index varies fastest inside each
axial ``J`` row.

Geometry/material cards
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Card
     - API interpretation
   * - ``2*``
     - Z fine-mesh boundaries, length ``JM + 1``
   * - ``4*``
     - R fine-mesh boundaries, length ``IM + 1``
   * - ``8$``
     - material-zone number for every fine-space cell
   * - ``9$``
     - cross-section reference associated with each DORT material zone
   * - ``84$``
     - edit-region number by material zone

Local negative ``9$$`` convention
---------------------------------

For the external-mixture workflow, mixture ID ``m`` and Legendre order ``L``
produce a first ``mixf.cr`` table number

.. math::

   t_m = 1 + (m-1)(L+1).

The locally modified DORT references that mixture as

.. math::

   IZMT = -t_m.

Therefore a P5 calculation uses the sequence ``-1, -7, -13, -19, ...``.

.. important::

   This negative ``9$$`` convention is specific to the verified local code and
   external ``mixf.cr`` workflow.  It should not be replaced by the stock DORT
   in-core mixing interpretation.

Cross-section file unit
-----------------------

The third field of ``61$$`` is ``NTSIG``.  The supplied local decks use:

.. code-block:: text

   NTSIG = 51
   file  = mixf.cr

The writer/run-control objects carry this association through
``cross_section_unit``.

Edit-region helpers
-------------------

``writer.array84_identity()``
   Uses edit-region numbers ``1, 2, ..., IZM``.

``writer.array84_by_material()``
   Groups zones by the natural API material ID.

Choose the mapping that matches the intended edit/output grouping; ``84$`` is
not a cross-section-material sequence.
