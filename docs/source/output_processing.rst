Process VARFLM Flux Output
==========================

``dortflux.bin`` on the ``NTFOG`` unit is a VARFLM file (DORT manual,
Section 4.6). It has five header records: identification, label, file
control, integer parameters, and real parameters. Each group then contains
one flux-moment record for each J interval and one boundary directional-flux
record. The scalar flux is the first moment of each J record. Record lengths
are checked against the header and both Fortran record markers are validated.

Inspect the file
----------------

.. code-block:: python

   from dort_input import DortFluxReader

   reader = DortFluxReader("run_01/dortflux.bin")
   meta = reader.metadata
   print(meta.group_count, meta.neutron_groups, meta.photon_groups)
   print(meta.shape)  # (group, J/axial, I/radial)
   print(meta.z_edges)
   print(meta.radial_edges(0))
   print(meta.power_watts, meta.effective_multiplication_factor)

The radial mesh can change between axial intervals. ``radial_edges(j)``
returns the appropriate boundary array, and the padded cells of arrays
returned by the reader are ``NaN``. Metadata from the file takes precedence
over independent ``Radii.txt`` and ``Heights.txt`` copies.

Compute flux and dose
---------------------

.. code-block:: python

   from dort_input import load_group_factors

   # Each text file has one numerical coefficient per line, in file order.
   nf = load_group_factors("NeutronDose.txt", meta.neutron_groups)
   gf = load_group_factors("GammaDose.txt", meta.photon_groups)
   dose = reader.dose_rate(nf, gf)  # neutron, photon, total; [J, I]
   summed_flux = reader.integrated_flux()
   specific_groups = reader.read_scalar_flux(groups=[0, 1, meta.neutron_groups])

``dose_rate`` and ``integrated_flux`` stream rows through the file and do
not allocate an array of every group. For a 175-neutron, 42-photon case,
the full cube can occupy more than 100 MB. ``weighted_sums(weights)``
accepts one coefficient per group or an array of several weight rows,
which permits other linear response functions in one pass.

The first ``NEUT`` groups in the file are neutrons, followed by photons.
Groups are stored in decreasing energy as described by the manual. Use the
file order when loading coefficients, including for an adjoint run, where
the manual says the output groups are in calculation order. No unit
conversion is implicit: multiply coefficients by flux units to determine
response units. Pass ``scale=3600.0`` only when converting a result in
units per second to units per hour.

Plot and save
-------------

.. code-block:: python

   import numpy as np

   fig, ax = reader.plot_field(dose.total, label="Dose rate", log=True)
   fig.savefig("dose_rate.png", dpi=180, bbox_inches="tight")
   reader.write_rz_csv(dose.total, "dose_total_rz.csv")
   np.savez_compressed("dose_fields.npz", neutron=dose.neutron,
                       photon=dose.photon, total=dose.total,
                       z_edges=meta.z_edges)

``plot_field`` reads the R-Z boundaries from the binary metadata. It
handles a regular grid with ``pcolormesh`` and variable I meshes with
cell polygons. The plot has one colorbar and no obscuring legend.
``write_rz_csv`` exports one ``[J, I]`` scalar field as ``R,Z,Value`` rows
at cell centres for Origin or Excel. You can pass ``dose.neutron``,
``dose.photon``, ``summed_flux.total``, or one selected group, for example
``reader.read_scalar_flux(groups=[0])[0]``. Variable-I mesh padding is
omitted. R and Z retain the units stored in the DORT file; values are
exported without rescaling or interpolation.

Supported layouts
-----------------

The reader detects little- or big-endian files with four- or eight-byte
Fortran sequential record markers and four- or eight-byte real arrays.
It validates record lengths and rejects damaged/truncated files. Compiler
split subrecords and DORT's alternate albedo format are not supported.
The first two label records are treated as opaque Hollerith data; mesh and
normalization values are read from the typed records. The current package
has no supplied real ``dortflux.bin`` fixture, so check an initial production
case against your trusted Fortran program before relying on dose values.
