# Examples

Run the comprehensive examples from the repository root:

```bash
python examples/comprehensive_mixture_spreadsheet.py
python examples/comprehensive_geometry.py
python examples/comprehensive_eigenvalue_first.py
python examples/comprehensive_eigenvalue_rerun.py
python examples/comprehensive_fixed_source.py
python examples/comprehensive_quadrature.py
```

Outputs are written below `example_output/`.

`examples/data/mixtures_example.xlsx` demonstrates the preferred spreadsheet
mixture layout: `Nuclide`, `MAT No.`, followed by one atom-density column per
final mixture. The spreadsheet example writes `mix.inp`, `Mixture_Names.txt`,
and DORT mixture mapping cards before using the imported mixture names in the
R-Z model.

The programmatic mixture definitions in some other examples are intentionally
kept to demonstrate the lower-level API. For routine work, the spreadsheet
workflow is the recommended entry point.
