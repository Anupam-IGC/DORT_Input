Overview and Conventions
========================

Design goal
-----------

The API is intended to make DORT input preparation **model-driven**.  Users
should describe physical intent—materials, regions, meshes, source locations,
and calculation mode—while the code handles positional DORT/FIDO arrays.

The project separates five concerns:

#. **Physical model** — materials, R-Z mesh, regions, priorities.
#. **Cross sections** — spreadsheet mixture import, external ``mix.inp`` preparation, and ``mixf.cr`` checks.
#. **Angular discretization** — DORT-compatible quadrature arrays.
#. **Run control** — human-readable settings mapped to ``61$$``/``62$$``/``63**``.
#. **Fixed source** — a mesh-aligned ``96**`` field and file-based ``98**`` spectrum.

Local cross-section convention
------------------------------

The recommended input is the standard Excel mixture table: ``Nuclide`` and
``MAT No.`` followed by one density column per final mixture.  Workbook-column
order becomes mixture order.

The supplied external mixer produces ``L+1`` consecutive tables per physical
mixture.  For mixture ID ``m`` and scattering order ``L``, the first table is

.. math::

   t_m = 1 + (m-1)(L+1).

The locally modified DORT uses ``-t_m`` in ``9$$``.  For P5 this gives
``-1, -7, -13, ...``.

The file ``mixf.cr`` is read on logical unit 51 in the verified sample decks;
this is the ``NTSIG`` position of ``61$$``.

Coordinate and array convention
-------------------------------

For R-Z geometry:

.. code-block:: text

   R >= 0
   Z may be negative, zero, or positive

All internal two-dimensional maps use

.. code-block:: text

   shape = (JM, IM) = (nz, nr)
   array[z_index, r_index]

The DORT writer serializes the R index first within each Z row.

What the API does not assume
----------------------------

The local DORT installation contains modifications that are not fully captured
by the stock manual.  The API therefore avoids inventing semantics for controls
that have not been verified from working local decks or source code.  Raw
controls remain available for exceptional cases.

.. seealso::

   * :doc:`user_guide/mixtures`
   * :doc:`user_guide/dort_mapping`
   * :doc:`user_guide/run_control`
