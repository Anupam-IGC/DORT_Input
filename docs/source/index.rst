DORT R-Z Input Preparation API
==============================

A Python interface for preparing **R-Z DORT calculations** using the verified
local workflow: geometry and material filling, external macroscopic mixture
preparation, angular quadrature, run-mode controls, and fixed-source spatial
fields.

.. note::

   This project follows a **locally modified DORT workflow**.  In particular,
   macroscopic mixtures are prepared externally and the resulting ``mixf.cr``
   tables are referenced through negative ``9$$`` entries.  The documentation
   describes the verified local behavior rather than silently substituting the
   stock DORT in-core mixing convention.

.. container:: doc-grid

   .. container:: doc-card

      **Start here**

      Build a small model, generate DORT fragments, and understand the overall
      workflow.

      :doc:`Open the quick start <getting_started>`

   .. container:: doc-card

      **User guide**

      Geometry, materials, external mixtures, run controls, fixed sources,
      quadrature, plotting, and writer details.

      :doc:`Browse the user guide <user_guide/index>`

   .. container:: doc-card

      **Comprehensive examples**

      End-to-end scripts for spreadsheet mixtures, geometry inspection,
      eigenvalue first/rerun calculations, fixed-source preparation, and quadrature.

      :doc:`Browse examples <examples/index>`

   .. container:: doc-card

      **API reference**

      Autodoc reference for the Python modules and public classes/functions.

      :doc:`Open API reference <api/index>`

Verified workflow
-----------------

.. code-block:: text

   mixture workbook / definitions
              |
              v
        define R-Z mesh
              |
              v
      define physical regions
              |
              v
        build + inspect model
              |
              +--------------------+
              |                    |
              v                    v
        external mixer        quadrature
     mix.inp -> mixf.cr       81*/82*/83*
              |                    |
              +---------+----------+
                        v
                 DORT writer
               2*/4*/8$/9$
                        |
                        v
                  run control
                 61$$/62$$/63**
                        |
             +----------+----------+
             |                     |
             v                     v
        eigenvalue            fixed source
       first / rerun          96** + 98**

Project scope
-------------

The API intentionally generates **validated input fragments** rather than
pretending to generate every possible locally modified DORT card.  Advanced or
site-specific cards can still be retained in a trusted template deck.

For a concise description of the design and conventions, see
:doc:`overview`.

.. toctree::
   :hidden:
   :maxdepth: 2

   overview
   getting_started
   installation
   user_guide/index
   examples/index
   api/index
   limitations
   roadmap
