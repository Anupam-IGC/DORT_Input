# NumPy-style docstring coverage

The updater covers the verified public API and important internal helpers in:

- `mesh.py`
- `materials.py`
- `regions.py`
- `model.py`
- `plotting.py`
- `writer.py`

It updates module docstrings plus public classes, properties, and methods.
The updater changes **docstrings only** and validates the resulting Python
syntax with `ast.parse()` before writing each file.

## Applying the update

From the repository root:

```bash
python tools/apply_numpy_docstrings.py
git diff
```

Then run your existing model/example tests before committing.

## Quadrature source

The accessible repository snapshot does not contain the newly mentioned
quadrature source module, and its README still states that quadrature generation
is not implemented. For that reason this package does not invent a quadrature
class/function API.

The Read-the-Docs guide is nevertheless updated with the quadrature processing
stage and the DORT input contract (`81*`, `82*`, `83*`, plus the variable-M-set
controls where applicable). Once the actual quadrature source file is present,
add an `api/quadrature.rst` page using `automodule`.
