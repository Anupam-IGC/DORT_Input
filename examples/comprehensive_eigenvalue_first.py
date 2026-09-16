"""Comprehensive first-eigenvalue workflow.

This example combines:
- external mixture input generation;
- R-Z geometry and region priorities;
- local negative 9$$ references;
- legacy S8 angular quadrature;
- human-readable first-eigenvalue run controls.

Run from the repository root:

    python examples/comprehensive_eigenvalue_first.py
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
    model = DORTModel("eigenvalue_first_demo")

    # The MAT numbers/densities below reproduce the supplied mixer-input sample.
    # Replace them with the actual recipes required by your microscopic library.
    model.add_mixture(
        "Mixture-1",
        {5125: 1.10597e-2, 5131: 8.27546e-3, 825: 2.90028e-2},
        legendre_order=5,
    )
    model.add_mixture("Mixture-2", {425: 1.1107e-1})
    model.add_mixture("Mixture-3", {725: 1.89693e-5, 825: 8.15551e-5})

    model.mesh.r.add_segment(0.0, 80.0, step=5.0)
    model.mesh.r.add_segment(80.0, 120.0, step=2.0)
    model.mesh.z.add_segment(-80.0, -40.0, step=5.0)
    model.mesh.z.add_segment(-40.0, 40.0, step=2.0)
    model.mesh.z.add_segment(40.0, 80.0, step=5.0)

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
    output_dir = ROOT / "example_output" / "eigenvalue_first"
    output_dir.mkdir(parents=True, exist_ok=True)

    model = build_model()

    # 1) Prepare input for the external microscopic-to-macroscopic mixer.
    mix_input = model.write_mixture_input(output_dir / "mix.inp")
    print(f"External mixer input: {mix_input}")

    # If a mixf.cr is already available in the example output directory, verify
    # that its table count/headers match the registered mixtures.
    mix_file = output_dir / "mixf.cr"
    if mix_file.exists():
        check = model.validate_mixture_file(mix_file)
        print(check.summary_text())
    else:
        print("Run m_ia_oa.for to create mixf.cr before the DORT calculation.")

    # 2) Generate geometry/material arrays.  For P5 the local 9$$ sequence for
    # these three mixtures is -1, -7, -13.
    writer = DORTWriter(
        model,
        zone_policy="region",
        cross_section_unit=51,
        cross_section_filename="mixf.cr",
    )
    writer.write_block4_fragment(output_dir / "geometry_material.inc")
    print(writer.material_layout_text())

    # 3) Reproduce a conventional legacy S8 angular quadrature.
    quadrature = generate_legacy_quadrature(order=8, symmetry="half")
    print(quadrature.summary_text())
    print(quadrature.validation_text())
    quadrature.write_dort(output_dir / "quadrature_s8.inc")

    # 4) Choose the first-eigenvalue preset and tune it with readable names.
    run = writer.create_run_control(
        "eigenvalue_first",
        energy_groups=217,
        quadrature_directions=quadrature.direction_count,
        neutron_groups=175,
        maximum_outer_iterations=20,
        initial_inner_iterations=30,
        final_inner_iterations=20,
        left_boundary="reflected",
        right_boundary="void",
        bottom_boundary="void",
        top_boundary="void",
        flux_extrapolation="theta_weighted",
        scalar_flux_printing="none",
        cross_section_printing="suppress",
    )

    (output_dir / "run_control.inc").write_text(
        run.control_fragment() + "\n",
        encoding="utf-8",
    )

    print("\nRUN SETTINGS")
    print(run.settings_help())
    print("\nOPTIONAL CARD POLICY")
    print(run.card_policy.summary_text())

    print(f"\nFiles written to {output_dir}")
    print("Cards 93*/94*/95* are still required by this first-run preset and")
    print("should be supplied according to the chosen initial-flux convention.")


if __name__ == "__main__":
    main()
