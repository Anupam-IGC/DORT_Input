Conventions and Package Boundaries
==================================

This package follows conventions observed in the locally modified DORT
workflow. Confirm them against the executable and templates used at your site.

R-Z and array ordering
----------------------

Internal two-dimensional arrays use:

.. code-block:: text

   shape = (JM, IM) = (nz, nr)
   value = array[z_index, r_index]

During DORT serialization, radial ``I`` varies fastest within each axial ``J``
row. Radial coordinates must be non-negative; axial coordinates may be
negative.

Regions are rectangular R-Z selections evaluated at cell centres:

.. code-block:: text

   r_min <= r_center < r_max
   z_min <= z_center < z_max

The exclusive upper bound keeps adjacent regions unambiguous. Higher-priority
regions overwrite lower-priority regions. Equal-priority overlap is rejected.

Geometry and material cards
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Card
     - Meaning in this package
   * - ``2**``
     - Z boundaries, containing ``JM + 1`` values
   * - ``4**``
     - R boundaries, containing ``IM + 1`` values
   * - ``8$$``
     - DORT zone number for every cell
   * - ``9$$``
     - local cross-section reference for every DORT zone
   * - ``84$$``
     - optional edit-region grouping by zone

The default ``zone_policy="material"`` merges all cells using the same
material into one DORT zone. With 29 used mixtures, ``IZM`` is 29 and ``9$$``
has exactly 29 references in material-registration (workbook) order.
``zone_policy="region"`` instead preserves each final physical-region owner as
a separate DORT zone; its ``9$$`` repeats a mixture reference for each such
zone and ``IZM`` increases to match. In both cases ``8$$`` refers to the zone
numbers used by ``9$$``. The ``9$$`` card ends with ``t``.

External mixtures and negative ``9$$`` values
----------------------------------------------

For Legendre order :math:`L`, each mixture occupies :math:`L+1` sequential
``mixf.cr`` tables. Mixture :math:`m` begins at:

.. math::

   t_m = 1 + (m-1)(L+1).

The verified local modified-DORT convention writes ``-t_m`` in ``9$$``. A P5
library therefore begins ``-1, -7, -13, -19, ...``. This is not the stock DORT
in-core mixing convention.

The package writes ``mix.inp`` and mapping aids. The external ``m_ia_oa.for``
mixer and nuclear-data library create ``mixf.cr``; they are not bundled or run
by this package.

File units used by the profiles
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 25 53

   * - DORT field
     - Default unit/file
     - Purpose
   * - ``NTSIG``
     - unit 51 / ``mixf.cr``
     - externally mixed cross sections
   * - ``NTFLX``
     - unit 20 / ``guessflux.bin``
     - eigenvalue restart input
   * - ``NTFOG``
     - unit 21 / ``dortflux.bin``
     - unformatted flux output for a future restart
   * - ``NTDSI``
     - unit 23
     - distributed fixed-source input association

Use the values required by the local launcher when they differ. Restart flux
files are copied byte-for-byte; the package does not decode Fortran
unformatted records.

Responsibility boundary
-----------------------

The package generates validated fragments, not a universal complete deck.

It handles:

* mixture bookkeeping and mapping files;
* piecewise R-Z mesh and rectangular-region filling;
* plots, cell inspection, zone construction, and geometry/material fragments;
* legacy and product quadrature generation and numerical validation;
* three high-level run profiles and optional-card policy checks;
* the ``INPSRM=2`` fixed-source form using ``96**`` and ``98**``.

You must still supply and review:

* the DORT executable, external mixer, and nuclear-data libraries;
* physically correct material compositions, spectra, and model dimensions;
* site-specific template cards and launcher/file associations;
* a physically motivated nonuniform initial-flux guess when required;
* solver benchmarks and mesh, quadrature, and scattering-order convergence.

The source builder does not generate the full-by-group ``INPSRM=1`` or
three-factor ``INPSRM=3`` representations. Locally modified ``62$$`` controls
outside the readable API can be set with ``run.set_raw_dort62(...)``, but such
overrides should be isolated and justified against local source documentation.
