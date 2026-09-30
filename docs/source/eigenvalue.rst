Eigenvalue Inputs
=================

Build and inspect the spatial model before adding eigenvalue controls. The two
profiles differ mainly in how the starting flux is supplied.

.. list-table::
   :header-rows: 1
   :widths: 25 25 22 28

   * - Profile
     - Starting flux
     - Required optional cards
     - Use
   * - ``eigenvalue_first``
     - factorized input
     - ``93*``, ``94*``, ``95*``
     - first calculation
   * - ``eigenvalue_rerun``
     - unit-20 restart file
     - none of ``93*``--``98*``
     - continue a previous calculation

The supplied tutorial workbook is not a critical benchmark. Use a reviewed
fissile-material library, geometry, and solver settings for a physical
eigenvalue calculation.

First calculation
-----------------

After creating a writer and validated quadrature:

.. code-block:: python

   from pathlib import Path

   from dort_input import generate_legacy_quadrature

   quadrature = generate_legacy_quadrature(order=8, symmetry="half")
   report = quadrature.validate(require_positive_weights=False)
   if not report.valid:
       raise RuntimeError(report.text())

   run = writer.create_run_control(
       "eigenvalue_first",
       energy_groups=217,
       quadrature_directions=quadrature.direction_count,
       neutron_groups=175,
       maximum_outer_iterations=20,
       initial_inner_iterations=30,
       final_inner_iterations=20,
       left_boundary="reflected",
       right_boundary="void",
       bottom_boundary="void",
       top_boundary="void",
       flux_extrapolation="theta_weighted",
   )
   run.validate()

   # Supply the reviewed 1** array in actual group order, including photons.
   group_values = [1.0 / 175] * 175 + [0.0] * 42  # Teaching values.
   writer.write_complete_input(
       "dortinp_first.inp", run_control=run, quadrature=quadrature,
       array1=group_values, title="First eigenvalue case",
   )

The writer transfers ``ISCTM``, ``IZM``, ``IM``, and ``JM`` from the built
model. ``MM`` comes from the actual quadrature direction count, which avoids
duplicating those values by hand.

Starting-flux cards
~~~~~~~~~~~~~~~~~~~

The first-run preset uses a factorized starting flux. The package writes
``93** F 1.0 t``, ``94** F 1.0 t``, and ``95** F 1.0 t`` after the geometry
block, each as a separate terminated card. This exact form was accepted by the
local DORT 2.8.14 input reader. Use
``run.initial_flux_fragment(value=2.0)`` to request another positive uniform
value, or replace the cards when a spatial or group-dependent guess is needed.
For a complete deck, pass ``initial_flux=2.0`` to
``writer.write_complete_input(...)``.

The combined writer emits a ``t`` after 63**, another for the empty block,
then quadrature in 82**/83**/81** order followed by 84$$ and ``t``. The next
block contains 1**, 2**, 4**, 8$$ and 9$$ with ``t``. Starting-flux cards and
a final ``t`` follow. The 1** data come from the problem, not the geometry
model; pass ``IGM`` numbers or a preformatted 1** card.

Check the intended card set before assembling the full input:

.. code-block:: python

   result = run.validate_present_cards((93, 94, 95))
   if not result.valid:
       raise RuntimeError(result.summary_text())

This verifies presence only; it does not establish that the numerical values
are physically suitable.

Run the complete tutorial with:

.. code-block:: bash

   python examples/eigenvalue_input.py

Restart calculation
-------------------

The verified local file flow is:

.. code-block:: text

   previous run: unit 21 -> dortflux.bin
   next run:     unit 20 <- guessflux.bin

Create the restart profile with the same reviewed geometry, materials, group
structure, and quadrature:

.. code-block:: python

   rerun = writer.create_run_control(
       "eigenvalue_rerun",
       energy_groups=217,
       quadrature_directions=quadrature.direction_count,
       neutron_groups=175,
   )
   rerun.validate()

   # In the run directory, copy the previous unformatted flux byte-for-byte.
   rerun.prepare_rerun_flux("run_directory")

Restart mode uses ``INPFXM=0`` with a nonzero ``NTFLX``. Cards
``93*``--``98*`` are forbidden for this profile:

.. code-block:: python

   assert rerun.validate_present_cards(()).valid

Run the restart tutorial with:

.. code-block:: bash

   python examples/eigenvalue_restart.py

The script creates ``guessflux.bin`` only when ``dortflux.bin`` is present; it
otherwise prints the expected location without inventing a restart file.

Review before running DORT
--------------------------

* confirm the group structure and cross-section table positions;
* confirm the material is actually fissile and the model is a valid benchmark;
* compare boundary conditions and convergence settings with a working case;
* confirm the quadrature direction count equals ``MM``;
* inspect ``run.summary_text()`` and ``run.card_policy.summary_text()``;
* compare the assembled deck with the trusted local template.

See :doc:`validation` for the full pre-run gate.
