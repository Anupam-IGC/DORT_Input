Pre-Run Validation
==================

Treat validation as a release gate for each input, not as a final formatting
step. A Python object can be internally consistent while still representing
the wrong physical problem.

Review gate
-----------

.. list-table::
   :header-rows: 1
   :widths: 22 43 35

   * - Layer
     - Check
     - Evidence to keep
   * - Mixtures
     - names, order, MAT numbers, densities, Legendre order, table count
     - workbook, ``Mixture_Names.txt``, mixer log
   * - Mesh
     - domain limits, interface boundaries, refinement, ``IM`` and ``JM``
     - mesh definition and plotted grid
   * - Geometry
     - background, bounds, priorities, overlaps, cell ownership
     - counts plus material/region plots
   * - DORT mapping
     - ``IZM``, zone owners, negative ``9$$`` values, ``NTSIG`` unit
     - writer summary and zone table
   * - Quadrature
     - validation report, direction ordering, weight normalization, ``MM``
     - report, plots, benchmark reference
   * - Run controls
     - profile, boundaries, group counts, iterations, file units
     - run summary and reviewed ``61$$``/``62$$``
   * - Optional cards
     - required cards present and forbidden cards absent
     - card-policy validation result
   * - Assembly
     - fragment order and all site-specific template cards retained
     - diff against a known working input

Geometry checks in code
-----------------------

Build with strict region bounds and inspect the final maps:

.. code-block:: python

   warnings = model.validate(strict_region_bounds=True)
   summary = model.build(strict_region_bounds=True)

   print(warnings)
   print(summary)
   print(model.material_cell_counts())
   print(model.region_cell_counts())

   save_material_plot(model, "materials.png", show_mesh=True)
   save_region_plot(model, "regions.png", show_mesh=True)

For a focused inspection, restrict both plots to the same R-Z window. Material
boundaries and IDs are based on final cell assignments after priority overlaps:

.. code-block:: python

   window = dict(r_extent=(35.0, 85.0), z_extent=(-30.0, 30.0))
   save_material_plot(
       model, "material_detail.png", **window,
       show_material_boundaries=True, show_material_ids=True,
   )
   save_region_plot(model, "region_detail.png", **window)
   save_material_plot(model, "material_outline.png", **window,
                      color_fill=False)

``show_material_ids=True`` labels each visible connected material area once,
including separate islands with the same material ID. The older
``show_ids=True`` labels every mesh cell. Axes outside the requested window are
clipped, and partially visible cells contribute to label placement.
ID plots default to a wider figure and ``aspect="auto"`` to separate narrow
radial regions. For physical scale, use ``aspect="equal"``. The outline plot
contains only material boundaries, IDs, and an ID–name legend; it does not
fill areas with colors. The legend only includes materials in the visible view.
For dense models, use ``figsize=(14, 9)`` to increase the space available for
labels. If a label cannot fit within its region without overlapping another,
a short leader line connects it to that region.

Background cells report priority ``0`` and an intentionally unfilled cell
reports ``None`` from ``cell_assignment``. Check that repeated material names
in a geometry definition are stored in a list of ``(material, z_bounds)``
pairs rather than dictionary entries; Python silently discards earlier
intervals with repeated dictionary keys.

Use ``model.cell_assignment(z_index, r_index)`` for any surprising cell.
Confirm that all important physical interfaces coincide with mesh boundaries;
region selection is based on cell centres.

Writer and mixture checks
-------------------------

.. code-block:: python

   print(writer.summary_text())
   print(writer.material_layout_text())
   print(writer.zone_table_text())

Verify that the number and order of ``mixf.cr`` tables match the workbook and
scattering order. Confirm that ``cross_section_unit`` points to the file unit
used by the local run script.

Quadrature checks
-----------------

.. code-block:: python

   report = quadrature.validate(require_positive_weights=False)
   print(report.text())
   if not report.valid:
       raise RuntimeError("Quadrature validation failed")

The established legacy set may contain intentional zero-weight directions;
that is why its check permits zero weights. Alternative product sets should be
validated with the default positive-weight requirement and benchmarked in the
actual solver before production use.

Run-control and card checks
---------------------------

.. code-block:: python

   run.validate()
   print(run.summary_text())
   print(run.card_policy.summary_text())

After assembling the complete input, compare the deck itself:

.. code-block:: python

   from pathlib import Path

   deck = Path("dortinp").read_text(encoding="ascii")
   result = run.validate_deck_text(deck)
   print(result.summary_text())
   if not result.valid:
       raise RuntimeError("Deck and selected run profile disagree")

Use ``strict_controls=True`` for a field-by-field comparison of supplied
``61$$`` and ``62$$`` entries. The default comparison focuses on the fields
that define the calculation workflow.

Common failures
---------------

.. list-table::
   :header-rows: 1
   :widths: 32 33 35

   * - Symptom
     - Likely cause
     - Correction
   * - Unknown material name
     - workbook name and region name differ
     - use the exact registered mixture name
   * - Discontinuous mesh segment
     - next segment does not start at the previous endpoint
     - make adjacent endpoints identical
   * - Equal-priority overlap
     - two regions claim the same cell without precedence
     - fix bounds or assign intentional priorities
   * - Region outside mesh
     - bounds exceed the modeled domain
     - expand the mesh or correct the region
   * - Spectrum-length error
     - source values do not equal ``IGM``
     - use the exact library group count and ordering
   * - Missing ``93*``--``95*``
     - factorized starting flux selected but only ``control_fragment()`` written
     - write the complete input with ``writer.write_complete_input()``
   * - Restart rejected
     - wrong filename/unit or explicit flux cards remain
     - use unit 20 ``guessflux.bin`` and remove ``93*``--``98*``
   * - DORT material mismatch
     - workbook order, P-order, or ``mixf.cr`` changed
     - regenerate and re-review every mapping file

Final acceptance
----------------

Do not submit the calculation until the generated plots, summaries, fragments,
external files, and assembled-deck diff all describe the same model. Solver
execution and physics benchmarking remain separate acceptance steps.
