Fixed-Source Inputs
===================

The high-level source builder prepares the verified space-by-energy form:

.. code-block:: text

   96**  one R-Z spatial field
   98**  one value per energy group
   97**  not used

The spatial field uses the same final material, region, and zone maps that you
reviewed during geometry construction.

1. Create a source on the built model
-------------------------------------

.. code-block:: python

   source = writer.create_source(background=0.0)

The source shape is ``(JM, IM) == (nz, nr)``. Select cells by the most stable
description available:

.. code-block:: python

   # Final named-region ownership
   source.by_region("central_block", strength=1.0)

   # Final material, including every region that uses it
   source.by_material("B4C Powder", strength=0.05, combine="add")

   # Cell-centre selection within explicit R-Z bounds
   source.by_mesh(
       r=(10.0, 20.0),
       z=(-10.0, 10.0),
       strength=0.25,
       combine="add",
   )

``replace`` is the default combination rule. Use ``add`` or ``multiply`` only
when overlapping contributions are intentional. A source created from the
writer can also use ``source.by_zone(zone_id, strength=...)``.

For a custom field, supply an array with exactly ``model.mesh.shape`` or a
function evaluated at cell centres:

.. code-block:: python

   source.set_spatial_function(
       lambda r, z: 1.0 if r < 20.0 and abs(z) < 10.0 else 0.0
   )

2. Supply the energy spectrum
-----------------------------

The spectrum must contain exactly one value per DORT energy group:

.. code-block:: python

   import numpy as np

   spectrum = np.geomspace(1.0, 1.0e-4, 217)
   source.set_energy_spectrum(spectrum, normalize=True)

The tutorial spectrum is synthetic. Replace it with a justified source
spectrum and verify group ordering against the cross-section library.
Normalization is off by default when reading values directly or from a file,
so physical magnitude is preserved unless ``normalize=True`` is explicit.

Text files may contain whitespace-separated numbers, Fortran ``D`` exponents,
and simple FIDO repetition:

.. code-block:: python

   source.set_energy_spectrum_file("source_spectrum.txt")

3. Create and attach the run profile
------------------------------------

For the cleanest tutorial, use a zero starting flux. This avoids unrelated
``93*``--``95*`` cards while retaining the ``96**``/``98**`` source:

.. code-block:: python

   from pathlib import Path

   run = writer.create_run_control(
       "fixed_source",
       energy_groups=217,
       quadrature_directions=quadrature.direction_count,
       neutron_groups=175,
       starting_flux="zero",
       maximum_outer_iterations=20,
       left_boundary="reflected",
       right_boundary="void",
       bottom_boundary="void",
       top_boundary="void",
   )
   run.attach_source(source)
   run.validate()

Attachment checks the spatial shape and spectrum length. It selects the
``space_energy`` distributed-source form, which requires ``96**`` and ``98**``
and forbids ``97**``.

Write the complete input after supplying a reviewed group-wise 1** array:

.. code-block:: python

   writer.write_complete_input(
       "dortinp_fixed.inp", run_control=run, quadrature=quadrature,
       array1=[0.0] * 217,  # Replace with reviewed problem data.
       title="Fixed-source case",
   )

   result = run.validate_present_cards((96, 98))
   if not result.valid:
       raise RuntimeError(result.summary_text())

If you intentionally choose ``starting_flux="factorized"``,
With ``starting_flux="factorized"``, the combined writer inserts the
``93**``--``95**`` guess after geometry and before the source cards. It
defaults to ``1.0``.

4. Inspect the source
---------------------

Before serialization, check at least:

.. code-block:: python

   print(source.summary_text())
   print(source.spatial.shape)
   print(source.spatial.min(), source.spatial.max())
   print(run.card_policy.summary_text())

Plot the spatial array and confirm that its nonzero cells coincide with the
intended physical regions. The full example does this automatically:

.. code-block:: bash

   python examples/fixed_source_input.py

It demonstrates region, material, and mesh selectors, intentional addition of
overlapping contributions, spectrum validation, card generation, and source
plotting.
