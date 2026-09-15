DORT R-Z Input Preparation API
==============================

The **DORT R-Z Input Preparation API** is a lightweight Python interface for
preparing R-Z mesh geometry and material filling data for DORT calculations.

Instead of manually constructing large DORT zone arrays, the user describes a
model in terms of readable material names, radial and axial mesh segments,
rectangular physical regions, and region priorities. The API converts this
description into mesh-cell material/region maps and DORT/FIDO geometry-material
arrays.

.. note::

   The project is in early development. The current implementation focuses on
   R-Z mesh and material filling preparation. It does **not** yet generate a
   complete DORT problem deck.

Main capabilities
-----------------

* piecewise-uniform or explicit R and Z meshes,
* named material registration,
* rectangular R-Z regions,
* priority-based material filling,
* equal-priority overlap checking,
* material and region maps for verification,
* visual plotting of the final model,
* DORT material-zone generation,
* FIDO-formatted ``2*``, ``4*``, ``8$`` and ``9$`` arrays,
* optional identity ``84$`` edit-region mapping.

Typical workflow
----------------

.. code-block:: text

   create model
       ↓
   add materials
       ↓
   define R/Z mesh
       ↓
   set background
       ↓
   add regions and priorities
       ↓
   model.build()
       ↓
   inspect and plot
       ↓
   create DORTWriter
       ↓
   generate DORT/FIDO arrays

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started
   installation

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/mesh
   user_guide/materials
   user_guide/regions
   user_guide/building
   user_guide/inspection
   user_guide/plotting
   user_guide/quadrature
   user_guide/dort_writer
   user_guide/dort_mapping

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/basic_model
   examples/external_material_numbers

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/mesh
   api/materials
   api/regions
   api/model
   api/quadrature
   api/quadrature_plotting
   api/plotting
   api/writer

.. toctree::
   :maxdepth: 1
   :caption: Development

   limitations
   roadmap

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
