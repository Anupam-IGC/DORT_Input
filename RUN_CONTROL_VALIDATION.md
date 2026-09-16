# Validation against supplied DORT decks

The `run_control.py` card-policy validator was checked against the three input
files supplied on 16 Sep 2026.

| Supplied deck | Selected profile | Required 93*-98* cards | Forbidden 93*-98* cards | Result |
|---|---|---|---|---|
| eigenvalue first | `eigenvalue_first` | 93, 94, 95 | 96, 97, 98 | pass |
| eigenvalue rerun | `eigenvalue_rerun` | none | 93, 94, 95, 96, 97, 98 | pass |
| fixed source | `fixed_source` | 93, 94, 95, 96, 98 | 97 | pass |

The semantic validator also verified the relevant file-unit and 62$$ selectors:

- first eigenvalue: `NTFLX=0`, `NTFOG=21`, `NTSIG=51`, `KTYPE=1`,
  `INPFXM=3`, `INPSRM=0`, `NOFIS=0`;
- eigenvalue rerun: `NTFLX=20`, `NTFOG=21`, `NTSIG=51`, `KTYPE=1`,
  `INPFXM=0`, `INPSRM=0`, `NOFIS=0`;
- fixed source: `NTFLX=0`, `NTFOG=21`, `NTSIG=51`, `NTDSI=23`,
  `KTYPE=0`, `INPFXM=3`, `INPSRM=2`, `NOFIS=2`.

The rerun helper copies the unformatted `dortflux.bin` from unit 21 to
`guessflux.bin` for unit 20 without parsing or modifying the binary records.
