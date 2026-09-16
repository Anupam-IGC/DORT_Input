Examples
========

The examples are designed to be **run from the repository root** and to write
results into ``example_output/``.  They intentionally produce fragments rather
than pretending to assemble every site-specific DORT card.

Comprehensive workflows
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 28 44 28

   * - Example
     - Main features
     - Best starting point for
   * - :doc:`comprehensive_mixture_spreadsheet`
     - Excel mixture import, mix.inp/names/cards, zone-aware mapping
     - preparing macroscopic mixture inputs
   * - :doc:`comprehensive_geometry`
     - piecewise mesh, priorities, plots, zones, Block-4 arrays
     - learning the spatial-model API
   * - :doc:`comprehensive_eigenvalue_first`
     - external mixtures, quadrature, first eigenvalue run controls
     - a new criticality calculation
   * - :doc:`comprehensive_eigenvalue_rerun`
     - restart units 20/21, rerun controls, flux-file preparation
     - continuing an eigenvalue run
   * - :doc:`comprehensive_fixed_source`
     - source by region/material/mesh, spectrum file, 96**/98**
     - shielding/source calculations
   * - :doc:`comprehensive_quadrature`
     - legacy and product quadrature, validation, visualization
     - angular-discretization studies

Smaller focused examples
------------------------

The older focused examples are retained because they are useful for quickly
isolating one feature.

.. toctree::
   :maxdepth: 1

   comprehensive_mixture_spreadsheet
   comprehensive_geometry
   comprehensive_eigenvalue_first
   comprehensive_eigenvalue_rerun
   comprehensive_fixed_source
   comprehensive_quadrature
   basic_model
   mixing_materials
   run_modes
   fixed_source_spatial
   external_material_numbers
