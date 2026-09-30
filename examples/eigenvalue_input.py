"""Tutorial 2: prepare fragments for a first eigenvalue calculation.

The supplied workbook is a shielding-material demonstration, not a critical
benchmark. Replace it with a validated fissile-material workbook and validated
solver controls before performing a physical eigenvalue calculation.

Run from the repository root with::

    python examples/eigenvalue_input.py
"""

from pathlib import Path

import numpy as np

from dort_input import DORTWriter, generate_legacy_quadrature

from modeling_basics import ROOT, build_sample_model


OUTPUT_DIR = ROOT / "example_output" / "02_eigenvalue_input"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = build_sample_model()
    mixture_files = model.write_mixture_preparation_files(OUTPUT_DIR / "mixtures")

    writer = DORTWriter(
        model,
        zone_policy="material",
        cross_section_unit=51,
        cross_section_filename="mixf.cr",
    )

    # Start production work with the established quadrature used by the local
    # solver. Alternative product quadratures require separate verification.
    quadrature = generate_legacy_quadrature(order=8, symmetry="half")
    report = quadrature.validate(require_positive_weights=False)
    if not report.valid:
        raise RuntimeError(report.text())

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
    run.validate()

    geometry_file = writer.write_block4_fragment(
        OUTPUT_DIR / "geometry_material.inc"
    )
    quadrature_file = quadrature.write_dort(OUTPUT_DIR / "quadrature_s8.inc")
    control_file = OUTPUT_DIR / "run_control.inc"
    control_file.write_text(
        run.control_fragment() + "\n", encoding="ascii"
    )

    # Array 1** is a group-wise input from the user's reviewed problem data.
    # This normalized neutron shape and zero photon tail are tutorial values.
    neutron_shape = np.geomspace(1.0, 1.0e-3, 175)
    array1 = np.concatenate((neutron_shape / neutron_shape.sum(), np.zeros(42)))
    deck_file = writer.write_complete_input(
        OUTPUT_DIR / "dortinp_first.inp",
        run_control=run, quadrature=quadrature, array1=array1,
        title="Tutorial first eigenvalue input",
    )

    # The local DORT run accepted 93**/94**/95** as F 1.0 t.
    expected_cards = run.validate_present_cards((93, 94, 95))
    if not expected_cards.valid:
        raise RuntimeError(expected_cards.summary_text())

    print(writer.summary_text())
    print("\nQUADRATURE")
    print(quadrature.summary_text())
    print("\nRUN MODE")
    print(run.summary_text())
    print("\nOPTIONAL CARD POLICY")
    print(run.card_policy.summary_text())

    print("\nFILES")
    for label, path in mixture_files.items():
        print(f"{label:16s}: {path}")
    print(f"{'geometry':16s}: {geometry_file}")
    print(f"{'quadrature':16s}: {quadrature_file}")
    print(f"{'run control':16s}: {control_file}")
    print(f"{'combined input':16s}: {deck_file}")

    print("\nIMPORTANT")
    print("Replace the tutorial 1** array with your reviewed group data.")


if __name__ == "__main__":
    main()
