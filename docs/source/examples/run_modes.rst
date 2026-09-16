Human-Readable Run-Control Example
==================================

After constructing and building a model:

.. code-block:: python

   writer = DORTWriter(model, cross_section_unit=51)

First eigenvalue calculation
----------------------------

.. code-block:: python

   first = writer.create_run_control(
       "eigenvalue_first",
       energy_groups=217,
       quadrature_directions=48,
       neutron_groups=175,
       maximum_outer_iterations=15,
       left_boundary="reflected",
       right_boundary="void",
       flux_extrapolation="theta_weighted",
   )

   print(first.summary_text())
   print(first.settings_help())

To change the calculation without using DORT variable names:

.. code-block:: python

   first.configure(
       initial_inner_iterations=30,
       final_inner_iterations=20,
       scalar_flux_printing="after_each_group",
       cross_section_printing="suppress",
   )

To discover an option:

.. code-block:: python

   print(first.available_options("rebalance_method"))
   print(first.describe_setting("zone_convergence"))

Eigenvalue rerun
----------------

.. code-block:: python

   rerun = writer.create_run_control(
       "eigenvalue_rerun",
       energy_groups=217,
       quadrature_directions=48,
       neutron_groups=175,
   )

   rerun.prepare_rerun_flux(".")

The restart preset automatically selects ``starting_flux="restart_file"`` and
therefore suppresses cards 93*-95*.

Fixed-source calculation
------------------------

.. code-block:: python

   fixed = writer.create_run_control(
       "fixed_source",
       energy_groups=217,
       quadrature_directions=210,
       distributed_source="space_energy",
   )

   print(fixed.card_policy.summary_text())

The supplied fixed-source convention requires cards 93*, 94*, 95*, 96* and
98*.  If a different distributed-source representation is selected, the API
updates the required/forbidden card list automatically.
