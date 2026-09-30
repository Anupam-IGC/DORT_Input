"""Inspect a VARFLM file, compute dose fields, and save plot, CSV, and NPZ.

Run from the repository root, for example:

python examples/process_dort_output.py run_01/dortflux.bin \
    --neutron-factors NeutronDose.txt --photon-factors GammaDose.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from dort_input import DortFluxReader, load_group_factors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("flux_file", type=Path)
    parser.add_argument("--neutron-factors", type=Path, required=True)
    parser.add_argument("--photon-factors", type=Path, required=True)
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Explicit response unit multiplier (default: 1).")
    parser.add_argument("--output-dir", type=Path, default=Path("dort_results"))
    args = parser.parse_args()

    reader = DortFluxReader(args.flux_file)
    m = reader.metadata
    print(f"Groups: {m.neutron_groups} neutron + {m.photon_groups} photon")
    print(f"Mesh: {m.axial_intervals} axial x {m.max_radial_intervals} maximum radial")
    print(f"Outer iteration: {m.outer_iteration}; DORT power: {m.power_watts:g} W")

    neutron_factors = load_group_factors(args.neutron_factors, m.neutron_groups)
    photon_factors = load_group_factors(args.photon_factors, m.photon_groups)
    dose = reader.dose_rate(neutron_factors, photon_factors, scale=args.scale)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    radial_edges = np.full((len(m.r_edges_by_set), m.max_radial_intervals + 1),
                           np.nan)
    for index, edges in enumerate(m.r_edges_by_set):
        radial_edges[index, :len(edges)] = edges
    np.savez_compressed(args.output_dir / "dose_fields.npz",
                        neutron=dose.neutron, photon=dose.photon,
                        total=dose.total, z_edges=m.z_edges,
                        radial_edges_by_set=radial_edges,
                        set_per_axial_interval=m.set_per_axial_interval)
    fig, _ = reader.plot_field(dose.total, label="Dose rate", log=True)
    fig.savefig(args.output_dir / "dose_rate.png", dpi=180, bbox_inches="tight")
    reader.write_rz_csv(dose.total, args.output_dir / "dose_total_rz.csv")
    print(f"Wrote dose_fields.npz, dose_rate.png, and dose_total_rz.csv to {args.output_dir}")


if __name__ == "__main__":
    main()
