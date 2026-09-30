API Reference
=============

This section is generated from the Python docstrings. Most users should begin
with the :doc:`../quickstart` and :doc:`../modeling_workflow`, then return here
for exact method signatures.

High-level entry points
-----------------------

* :mod:`dort_input.model` — central :class:`dort_input.model.DORTModel` object.
* :mod:`dort_input.writer` — geometry/material serialization and access to run/source builders.
* :mod:`dort_input.run_control` — calculation presets and readable control settings.
* :mod:`dort_input.source` — fixed-source spatial field and group spectrum.
* :mod:`dort_input.output` — VARFLM scalar flux and dose post-processing.

Supporting modules
------------------

* :mod:`dort_input.mesh`, :mod:`dort_input.materials`,
  :mod:`dort_input.mixtures`, :mod:`dort_input.regions`
* :mod:`dort_input.quadrature`, :mod:`dort_input.quadrature_plotting`,
  :mod:`dort_input.plotting`

.. toctree::
   :maxdepth: 1

   model
   writer
   run_control
   source
   mesh
   materials
   mixtures
   regions
   quadrature
   quadrature_plotting
   plotting
   output
