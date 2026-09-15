Quadrature-Set Calculation and DORT Integration
===============================================

Angular quadrature is a separate part of DORT input preparation from the
spatial mesh/material-zone model.

Processing position
-------------------

The recommended workflow is:

.. code-block:: text

   define R-Z mesh and materials
       ↓
   define regions and priorities
       ↓
   build + validate the spatial model
       ↓
   calculate/select angular quadrature
       ↓
   validate directions and weights
       ↓
   map quadrature to DORT directional arrays
       ↓
   generate DORT input fragments
       ↓
   perform mesh / quadrature / scattering-order convergence checks

DORT directional arrays
-----------------------

For DORT, the directional quadrature specification is carried by three
secondary input arrays:

.. code-block:: text

   81*  W(M,MSET)     directional weights
   82*  EMU(M,MSET)   cosine with X/R direction
   83*  ETA(M,MSET)   cosine with Z/Q direction

For ordinary R-Z geometry, ``EMU`` is therefore the radial direction cosine
and ``ETA`` is the axial direction cosine.

A DORT-oriented quadrature component should ultimately provide three aligned
one-dimensional arrays for each M-set:

.. code-block:: python

   weights
   mu_r
   eta_z

with equal lengths.

Basic validation
----------------

Before formatting a set for DORT, verify at least:

* all weights are finite,
* all direction cosines are finite,
* each direction cosine lies within ``[-1, 1]`` within numerical tolerance,
* the three arrays have equal lengths,
* weight normalization matches the DORT convention used by the reference case,
* symmetry expansion/order agrees with the direction count supplied through
  ``MM``.

Fixed versus variable quadrature
--------------------------------

``MM`` is an integer control parameter in DORT ``62$``. For a conventional
single direction set, ``MM`` gives the maximum number of directions.

DORT also describes variable quadrature when ``MM < 0``. In that mode,
multiple M-sets can be assigned by spatial and energy super-zones. Relevant
arrays include:

.. code-block:: text

   73$  MMBMS(MSET)   number of directions in each M-set
   74$  ISZNG(IG)     super-group number by energy group
   75*  SZNBZ         J/Z super-mesh boundaries
   76*  SZNBR         I/R super-mesh boundaries
   87$  IJGSZ         M-set assignment by super-zone/super-group

The spatial/material writer should remain independent of this advanced
variable-quadrature logic unless that feature is explicitly implemented.

Compatibility warning for non-classical quadratures
----------------------------------------------------

Do not assume that every mathematically valid angular quadrature can be passed
directly to DORT.

The earlier orthogonal-polynomial/Gauss-type quadrature work associated with
this project produces direction sets that do not generally lie on the
geodesic/level structure expected by classical codes such as DORT. Therefore,
keep two concepts separate:

#. **quadrature calculation/analysis**, which may generate arbitrary directions
   and weights;
#. **DORT-compatible quadrature serialization**, which must satisfy DORT's
   directional-set requirements.

Documentation integration
-------------------------

When the actual quadrature source module is present in the repository, create
an API page such as:

.. code-block:: rst

   Quadrature API
   ==============

   .. automodule:: quadrature
      :members:
      :undoc-members:
      :show-inheritance:

and add that page to the API toctree. Sphinx will then extract the implemented
NumPy-style docstrings directly from the source.
