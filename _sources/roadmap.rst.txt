Development Roadmap
===================

A practical next-development sequence is:

Template/deck handling
----------------------

* read an existing DORT deck,
* replace ``2*``, ``4*``, ``8$``, ``9$`` and optionally ``84$``,
* update ``IZM``, ``IM`` and ``JM`` in ``62$``.

Additional geometry primitives
------------------------------

* axial layers,
* radial annuli,
* convenience vessel and shielding-region builders.

Material-library integration
----------------------------

* explicit mapping to GIP/DORT cross-section identifiers,
* validation of material references before export.

Alternative user frontends
--------------------------

* YAML input,
* Excel/tabular input,
* translation of those frontends into the same Python API.

Testing
-------

Add automated tests for:

* mesh generation,
* segment continuity,
* overlap detection,
* priority behavior,
* FIDO compression/expansion round trips,
* DORT ordering,
* comparison against known DORT inputs and outputs.


Quadrature integration
----------------------

* document the implemented quadrature-calculation API directly from its source,
* validate direction-cosine and weight normalization,
* generate DORT ``81*``, ``82*`` and ``83*`` arrays,
* update/control ``MM`` consistently in ``62$``,
* add variable M-set support (``73$``/``87$``) only when scientifically needed,
* regression-test quadrature output against a known DORT input/output case.
