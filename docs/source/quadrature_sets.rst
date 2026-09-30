Quadrature Sets and Directional Concentration
=============================================

The product quadrature provides angular directions and integration weights
for an R-Z DORT calculation. The three Cartesian cosines are radial :math:`r`,
azimuthal :math:`a`, and axial :math:`z`, with
:math:`r^2+a^2+z^2=1`. DORT stores radial and axial cosines; the positive
azimuthal cosine is reconstructed for plotting.

Choose ordinary or concentrated directions
--------------------------------------------

.. code-block:: python

   from dort_input import generate_product_quadrature

   ordinary = generate_product_quadrature(
       polar_order=24, azimuthal_order=32,
   )
   toward_positive_z = generate_product_quadrature(
       polar_order=24, azimuthal_order=32,
       bias_direction="+z", bias_fraction=0.75,
   )
   toward_positive_r = generate_product_quadrature(
       polar_order=24, azimuthal_order=32,
       bias_direction="+r", bias_fraction=0.75,
   )

Use ``+z``, ``-z``, ``+r``, or ``-r``. ``bias_fraction=0.75`` assigns 75% of
the relevant nodes to the chosen hemisphere. Each half uses its own
Gauss-Legendre integration, so the weights represent the **same uniform
angular measure** in every case. Bias changes where the set resolves a field
most finely; it does not amplify the physical flux in that direction. Axial
bias needs at least four polar levels in each hemisphere; radial bias needs at
least eight azimuthal nodes in each half to preserve angular moment accuracy.
The generator reports a useful error if the chosen orders are too small.

Check and write the result
--------------------------

.. code-block:: python

   q = toward_positive_z
   report = q.validate()
   if not report.valid:
       raise ValueError(report.text())
   print(q.summary_text())
   print(report.text())
   q.write_dort("quadrature.inc")
   mm = q.direction_count  # includes zero-weight level initiators

Check the moment-error line as well as ``report.valid``. Compare angular
resolution and transport results with a trusted baseline before selecting a
new quadrature for production.

Inspect the first octant
------------------------

.. code-block:: python

   from dort_input.quadrature_plotting import save_quadrature_3d_plot

   save_quadrature_3d_plot(q, "quadrature_first_octant.png")

The perspective looks toward the origin from outside the positive unit-sphere
octant. The plot includes only the positive radial, azimuthal, and axial
cosines with nonzero integration weight. Marker **area** follows the angular
weight and is reduced further where projected neighbors would overlap.
Zero-weight level initiators and legends are hidden by default. For very large
sets, enlarge the figure or zoom in to distinguish densely spaced directions.
