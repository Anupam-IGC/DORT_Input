Run Modes and Readable Controls
===============================

The run-control layer lets users choose physical/solver concepts using readable
names while DORT variable names remain an internal serialization detail.

Verified presets
----------------

.. list-table::
   :header-rows: 1
   :widths: 24 24 24 28

   * - Preset
     - Starting flux
     - Distributed source
     - Typical use
   * - ``eigenvalue_first``
     - ``factorized``
     - ``none``
     - first criticality calculation
   * - ``eigenvalue_rerun``
     - ``restart_file``
     - ``none``
     - continue from unit-21 flux output
   * - ``fixed_source``
     - ``factorized``
     - ``space_energy`` when a source is attached
     - shielding/source calculation

Create a profile
----------------

.. code-block:: python

   run = writer.create_run_control(
       "eigenvalue_first",
       energy_groups=217,
       quadrature_directions=48,
       neutron_groups=175,
       maximum_outer_iterations=20,
       initial_inner_iterations=30,
       final_inner_iterations=20,
       left_boundary="reflected",
       right_boundary="void",
       flux_extrapolation="theta_weighted",
   )

Change settings later with :meth:`run_control.DORTRunControl.configure`:

.. code-block:: python

   run.configure(
       rebalance_method="space_dependent",
       scalar_flux_printing="none",
       cross_section_printing="suppress",
   )

Discover options interactively
------------------------------

The public settings are intentionally discoverable:

.. code-block:: python

   print(run.available_options("left_boundary"))
   print(run.describe_setting("flux_extrapolation"))
   print(run.settings_help())

This is the preferred way to explore the API instead of memorizing positional
``62$$`` entries.

Frequently adjusted settings
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Public setting
     - Meaning / examples
   * - ``left_boundary``, ``right_boundary``, ``bottom_boundary``, ``top_boundary``
     - ``void``, ``reflected``, ``periodic``, ``cylindrical``, ``fixed_source``, ``albedo``
   * - ``maximum_outer_iterations``
     - maximum source/outer iterations
   * - ``initial_inner_iterations``, ``final_inner_iterations``
     - flux-iteration limits per group
   * - ``flux_extrapolation``
     - ``linear``, ``theta_weighted``, ``vector_weighted``, etc.
   * - ``rebalance_method``
     - ``groupwise``, ``source_correction``, ``space_dependent``
   * - ``scalar_flux_printing``
     - ``final``, ``none``, ``after_each_group``
   * - ``cross_section_printing``
     - ``print`` or ``suppress``
   * - ``directional_flux_output``
     - ``none``, ``save_only``, ``save_and_print``
   * - ``zone_convergence``
     - zone-convergence checking/printing behavior
   * - ``repair_negative_sources``
     - Boolean source repair switch

Automatic model-derived settings
--------------------------------

The following are visible but read-only because they come from the built model:

.. code-block:: text

   scattering_order
   material_zone_count
   radial_intervals
   axial_intervals

This prevents the run-control card from drifting out of sync with the geometry.

Eigenvalue rerun files
----------------------

The verified local restart convention is:

.. code-block:: text

   previous run: unit 21 -> dortflux.bin   (unformatted)
   next run:     unit 20 <- guessflux.bin  (unformatted)

Prepare the next run with:

.. code-block:: python

   rerun.prepare_rerun_flux("run_directory")

The copy is byte-for-byte; the API does not attempt to decode the Fortran
unformatted file.

Optional-card policy
--------------------

The profile derives the validity of cards ``93*`` through ``98*`` from the
selected starting-flux and distributed-source representations:

.. code-block:: python

   print(run.card_policy.summary_text())

For example, the fixed-source ``space_energy`` representation requires ``96**``
and ``98**`` and forbids ``97**``.

Validate an existing deck
-------------------------

.. code-block:: python

   text = Path("dortinp").read_text()
   result = run.validate_deck_text(text)
   print(result.summary_text())

Use ``strict_controls=True`` when you want a field-by-field ``61$$``/``62$$``
comparison rather than only the run-defining semantics.

Advanced raw controls
---------------------

For a locally modified DORT option that is not yet exposed by a readable name:

.. code-block:: python

   run.set_raw_dort62(LOCOBJ=0, LCMOBJ=0)

Keep raw overrides isolated and documented; ordinary scripts should prefer
``configure()``.

.. seealso::

   :doc:`../examples/comprehensive_eigenvalue_first`,
   :doc:`../examples/comprehensive_eigenvalue_rerun`, and
   :doc:`../examples/comprehensive_fixed_source`.
