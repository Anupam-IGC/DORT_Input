# Spreadsheet Mixture Processing Update

This update makes the attached Excel-driven `mixture.py` workflow the preferred
mixture-preparation interface for the DORT Input Preparation API.

## Main changes

- `mixtures.py`
  - reads the `Read` worksheet format (`Nuclide`, `MAT No.`, then mixture columns);
  - preserves spreadsheet column order as mixture IDs;
  - retains readable nuclide labels;
  - writes `mix.inp`, `Mixture_Names.txt`, and compact `dort_mix_cards.txt`;
  - keeps programmatic mixture definitions as an alternative;
  - validates spreadsheet structure, MAT numbers, densities, duplicates, and mixer limits.
- `model.py`
  - adds `load_mixtures_from_excel(...)`;
  - adds `prepare_mixtures_from_excel(...)`;
  - adds `write_mixture_preparation_files(...)`.
- `writer.py`
  - adds zone-aware `mixture_cards_fragment()` and `write_mixture_cards()` for
    geometries where `zone_policy="region"` creates more zones than mixtures.
- `mixture.py`
  - replaces the hard-coded standalone script with an API-backed CLI while
    retaining the old workbook/sheet/P5 defaults.
- `requirements.txt`
  - adds pandas and openpyxl for `.xlsx` input.
- Documentation
  - spreadsheet workflow is now the recommended path;
  - new comprehensive spreadsheet example and sample workbook;
  - compact versus zone-aware `84$$/9$$` behavior is documented explicitly.

## Verified attached workbook

For `examples/data/mixtures_example.xlsx` at P5, the mixture sequence is:

1. Sodium
2. Argon
3. Graphite
4. Lead
5. B4C Powder
6. Carbon Steel

and the compact cards are:

```text
84$$ 1 2 3 4 5 6 t
9$$ -1 -7 -13 -19 -25 -31 t
```

The generated files were compared against the original attached `mixture.py`
and are token-identical.
