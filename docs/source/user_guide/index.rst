User Guide
==========

Use this section when you want to understand **why** the API generates a
particular DORT fragment or how to configure one part of a calculation.

.. container:: doc-grid

   .. container:: doc-card

      **Build the spatial model**

      Mesh construction, materials, regions, priorities, model building, and
      inspection.

      :doc:`mesh` · :doc:`materials` · :doc:`regions` · :doc:`building`

   .. container:: doc-card

      **Prepare cross sections**

      Spreadsheet-driven mixture composition, ``mix.inp``/name/card generation,
      ``mixf.cr`` table numbering, validation, and negative local ``9$$`` references.

      :doc:`mixtures` · :doc:`dort_mapping`

   .. container:: doc-card

      **Choose calculation controls**

      Human-readable run settings for first eigenvalue, rerun, and fixed-source
      calculations.

      :doc:`run_control`

   .. container:: doc-card

      **Define fixed sources**

      Select source cells by material, region, DORT zone, mesh coordinates, or
      a spatial function; read the energy spectrum from file.

      :doc:`fixed_source`

   .. container:: doc-card

      **Angular quadrature**

      Legacy DOQDP-compatible sets and positive-weight product quadrature.

      :doc:`quadrature`

   .. container:: doc-card

      **Inspect and export**

      Plotting, writer output, zone tables, and model validation.

      :doc:`inspection` · :doc:`plotting` · :doc:`dort_writer`

.. toctree::
   :hidden:
   :maxdepth: 1

   mesh
   materials
   mixtures
   regions
   building
   inspection
   plotting
   quadrature
   run_control
   fixed_source
   dort_writer
   dort_mapping
