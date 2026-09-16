Fixed-Source Spatial Distribution
=================================

The verified local fixed-source workflow uses the ``space_energy`` distributed
source representation:

.. code-block:: text

   96**  two-dimensional R-Z spatial source
   98**  one value per energy group
   97**  not used

This maps naturally onto the existing geometry: define *where* the source is
using materials/regions/zones/mesh coordinates, then read its group dependence
from a separate spectrum file.

Create a source builder
-----------------------

.. code-block:: python

   source = writer.create_source(background=1.0e-20)

The source array has the same shape and ordering as the final model maps:

.. code-block:: text

   shape = (JM, IM) = (nz, nr)
   source[z_index, r_index]

Spatial selectors
-----------------

By final material
~~~~~~~~~~~~~~~~~

.. code-block:: python

   source.by_material("Fuel", strength=1.0)

   source.by_material({
       "Inner fuel": 1.0,
       "Outer fuel": 0.75,
       "Blanket": 0.10,
   })

By final region
~~~~~~~~~~~~~~~

.. code-block:: python

   source.by_region("inner_core", strength=1.0)
   source.by_region("outer_core", strength=0.8)

Region selection is especially useful when the same material appears in more
than one physical location.

By generated DORT zone
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   source.by_zone({3: 1.0, 4: 0.5})

This requires the source to be created from :class:`writer.DORTWriter`.

By R-Z mesh interval
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   source.by_mesh(
       r=(0.0, 50.0),
       z=(-25.0, 25.0),
       strength=1.0,
   )

Selection is based on cell centres.

Combine contributions
---------------------

Later selections replace earlier values by default.  For overlapping source
contributions, choose another combination rule:

.. code-block:: python

   source.by_region("fuel", strength=1.0)
   source.by_mesh(
       r=(0.0, 20.0),
       z=(-10.0, 10.0),
       strength=0.2,
       combine="add",
   )

Supported modes are ``replace``, ``add``, and ``multiply``.

Arbitrary spatial functions
---------------------------

.. code-block:: python

   import numpy as np

   source.set_spatial_function(
       lambda r, z: np.exp(-(z / 50.0) ** 2) if r < 100.0 else 0.0
   )

A complete NumPy array may also be supplied with
:meth:`source.FixedSource.set_spatial_array`.

Energy spectrum from file
-------------------------

The spectrum reader accepts whitespace-separated values, Fortran ``D``
exponents, and simple FIDO repetition:

.. code-block:: text

   1.240E-02
   6.317D-03
   42R 0.0

Load it with:

.. code-block:: python

   source.set_energy_spectrum_file("source_spectrum.txt")

Normalization is **off by default** so physical source magnitude is preserved.
Use ``normalize=True`` only when that is the intended convention.

Attach to a fixed-source run
----------------------------

.. code-block:: python

   run = writer.create_run_control(
       "fixed_source",
       energy_groups=217,
       quadrature_directions=48,
   )
   run.attach_source(source)

Attachment checks the mesh shape and requires exactly ``IGM`` spectrum values.
It also selects the ``space_energy`` distributed-source representation.

Generate cards
--------------

.. code-block:: python

   print(source.array96())
   print(source.array98(energy_groups=217))
   print(run.source_fragment())
   print(run.control_and_source_fragment())

The ``96**`` writer uses ``R`` compression within radial rows and ``Q``
compression for repeated complete Z rows.

.. seealso::

   :doc:`../examples/comprehensive_fixed_source` for an end-to-end example.
