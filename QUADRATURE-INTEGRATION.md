# Quadrature source integration note

The verified source snapshot used for this documentation bundle contains
`mesh.py`, `materials.py`, `regions.py`, `model.py`, `plotting.py`, and
`writer.py`, but no quadrature module.

When the actual new quadrature module is copied into the repository:

1. Run `python tools/apply_numpy_docstrings.py` for the six verified modules.
2. Add NumPy-style docstrings to the quadrature module based on its actual
   classes/functions rather than guessed signatures.
3. Create `docs/source/api/quadrature.rst`:

```rst
Quadrature API
==============

.. automodule:: quadrature
   :members:
   :undoc-members:
   :show-inheritance:
```

4. Add `api/quadrature` to the API Reference toctree.
5. If writer support exists, document the mapping to:
   - `81*` directional weights,
   - `82*` R-direction cosines,
   - `83*` Z-direction cosines.
6. For variable quadrature, document `MM < 0`, `73$ MMBMS`, and `87$ IJGSZ`.
