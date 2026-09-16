External Mixture Preparation Example
====================================

This reproduces the supplied three-mixture sample input.

.. code-block:: python

   from model import DORTModel

   model = DORTModel("mixture_sample")

   model.add_mixture(
       "Mixture-1",
       {5125: 1.10597e-2, 5131: 8.27546e-3, 825: 2.90028e-2},
       legendre_order=5,
   )
   model.add_mixture("Mixture-2", {425: 1.1107e-1})
   model.add_mixture("Mixture-3", {725: 1.89693e-5, 825: 8.15551e-5})

   print(model.render_mixture_input())
   model.write_mixture_input("mix.inp")

The expected cross-section-table layout is:

.. code-block:: text

   Mixture-1  tables  1..6   9$ =  -1
   Mixture-2  tables  7..12  9$ =  -7
   Mixture-3  tables 13..18  9$ = -13
