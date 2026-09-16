"""Comprehensive eigenvalue rerun/restart workflow.

The verified local convention is:

    previous run: unit 21 -> dortflux.bin  (unformatted)
    next run:     unit 20 <- guessflux.bin (unformatted)

Run from the repository root:

    python examples/comprehensive_eigenvalue_rerun.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import DORTModel
from quadrature import generate_legacy_quadrature
from writer import DORTWriter


def build_model() -> DORTModel:
    model = DORTModel("eigenvalue_rerun_demo")
    model.add_mixture(
        "Mixture-1",
        {5125: 1.10597e-2, 5131: 8.27546e-3, 825: 2.90028e-2},
        legendre_order=5,
    )
    model.add_mixture("Mixture-2", {425: 1.1107e-1})
    model.add_mixture("Mixture-3", {725: 1.89693e-5, 825: 8.15551e-5})

    model.mesh.r.add_segment(0.0, 80.0, step=5.0)
    model.mesh.r.add_segment(80.0, 120.0, step=2.0)
    model.mesh.z.add_segment(-80.0, 80.0, step=5.0)
    model.set_background("Mixture-1")
    model.add_region(
        "central_region",
        material="Mixture-2",
        r=(0.0, 80.0),
        z=(-40.0, 40.0),
        priority=20,
    )
    model.add_region(
        "radial_shield",
        material="Mixture-3",
        r=(80.0, 120.0),
        z=(-50.0, 50.0),
        priority=30,
    )
    model.build()
    return model


def main() -> None:
    output_dir = ROOT / "example_output" / "eigenvalue_rerun"
    output_dir.mkdir(parents=True, exist_ok=True)

    model = build_model()
    writer = DORTWriter(model, cross_section_unit=51)

    quadrature = generate_legacy_quadrature(order=8, symmetry="half")

    rerun = writer.create_run_control(
        "eigenvalue_rerun",
        energy_groups=217,
        quadrature_directions=quadrature.direction_count,
        neutron_groups=175,
        maximum_outer_iterations=30,
        initial_inner_iterations=20,
        final_inner_iterations=20,
        left_boundary="reflected",
        right_boundary="void",
        scalar_flux_printing="none",
    )

    writer.write_block4_fragment(output_dir / "geometry_material.inc")
    quadrature.write_dort(output_dir / "quadrature_s8.inc")
    (output_dir / "run_control.inc").write_text(
        rerun.control_fragment() + "\n",
        encoding="utf-8",
    )

    print(rerun.summary_text())
    print("\nFILE UNITS")
    print(rerun.file_units)
    print("\nOPTIONAL CARD POLICY")
    print(rerun.card_policy.summary_text())

    # Demonstrate the restart copy only when a previous flux file is present.
    previous_flux = output_dir / "dortflux.bin"
    if previous_flux.exists():
        next_guess = rerun.prepare_rerun_flux(output_dir, overwrite=True)
        print(f"Prepared restart file: {next_guess}")
    else:
        print(
            f"Place the previous unformatted flux output at {previous_flux} and "
            "rerun this example to create guessflux.bin."
        )

    print(f"\nFiles written to {output_dir}")


if __name__ == "__main__":
    main()
