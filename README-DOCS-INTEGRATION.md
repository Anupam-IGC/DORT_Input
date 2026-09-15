# Read the Docs integration files

Copy the contents of this bundle into the root of the `DORT_Input` repository.

It adds:

- `.readthedocs.yaml`
- `docs/requirements.txt`
- `docs/Makefile`
- `docs/make.bat`
- `docs/source/conf.py`
- structured Sphinx pages for installation, user guide, examples, API reference,
  limitations, and roadmap.

The existing runtime `requirements.txt` must remain at the repository root
because `.readthedocs.yaml` installs it before Sphinx imports the project modules.

Local build:

```bash
pip install -r requirements.txt
pip install -r docs/requirements.txt
cd docs
make html
```

Windows:

```bat
pip install -r requirements.txt
pip install -r docs/requirements.txt
cd docs
make.bat html
```

Then open:

`docs/build/html/index.html`

Because the project currently uses top-level modules rather than a packaged
Python distribution, `docs/source/conf.py` adds the repository root to
`sys.path` for `autodoc`.


## NumPy-style source docstrings

This update includes:

- `tools/apply_numpy_docstrings.py`
- `tools/numpy_docstrings.json`
- `tools/DOCSTRING_COVERAGE.md`
- `tools/check_numpy_docstrings.py`

Copy `tools/` into the repository root, then run:

```bash
python tools/apply_numpy_docstrings.py
git diff
```

The updater changes docstrings only in the six verified source modules and
syntax-checks each modified file before writing it.

## Quadrature processing

The user guide now includes
`docs/source/user_guide/quadrature.rst`, covering the quadrature stage and the
DORT mapping to `81*`, `82*`, and `83*`.

The actual quadrature source file was not present in the accessible repository
snapshot, so this bundle deliberately does not invent its public API. See
`QUADRATURE-INTEGRATION.md`.
