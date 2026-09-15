Current Limitations
===================

The current API intentionally targets R-Z mesh and material filling first.

The following are not yet implemented:

* full automatic DORT deck generation,
* automatic update/replacement of ``62$``,
* automatic insertion into an existing template deck,
* arbitrary non-rectangular region primitives,
* curved boundaries beyond rectangular R-Z cell-centre representation,
* fractionally mixed cells at region boundaries,
* DORT variable-I mesh (``IM < 0``),
* coarse-mesh ``85*`` and ``86*`` generation,
* cross-section mixing ``10$``, ``11$``, ``12*`` and ``13$`` generation,
* source definition,
* energy-group arrays,
* automatic execution of DORT,
* parsing/validation of a complete DORT output.

The documentation should be updated as each of these capabilities is added.


Quadrature status
-----------------

Quadrature-set calculation is now part of the documented processing workflow.
However, the quadrature source module was not present in the verified source
snapshot used to create this bundle. Consequently, the current ``DORTWriter``
still does not serialize ``81*``, ``82*`` or ``83*`` automatically.

The documentation intentionally avoids inventing a quadrature class or
function signature. Once the actual module is present, add it to the Sphinx
API reference and connect it to a dedicated quadrature writer.
