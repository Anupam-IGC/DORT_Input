"""Tutorial 4: prepare an eigenvalue restart using the previous flux file.

The local convention demonstrated here is:

* previous run writes unit 21 as ``dortflux.bin``;
* the next run reads unit 20 as ``guessflux.bin``.

Run from the repository root with::

    python examples/eigenvalue_restart.py
"""

import numpy as np

from dort_input import DORTWriter, generate_legacy_quadrature

from modeling_basics import ROOT, build_sample_model


OUTPUT_DIR = ROOT / "example_output" / "04_eigenvalue_restart"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = build_sample_model()
    model.write_mixture_preparation_files(OUTPUT_DIR / "mixtures")
    writer = DORTWriter(
        model,
        zone_policy="material",
        cross_section_unit=51,
        cross_section_filename="mixf.cr",
    )
    quadrature = generate_legacy_quadrature(order=8, symmetry="half")

    run = writer.create_run_control(
        "eigenvalue_rerun",
        energy_groups=217,
        quadrature_directions=quadrature.direction_count,
        neutron_groups=175,
        maximum_outer_iterations=30,
        initial_inner_iterations=20,
        final_inner_iterations=20,
        left_boundary="reflected",
        right_boundary="void",
        bottom_boundary="void",
        top_boundary="void",
        scalar_flux_printing="none",
    )
    run.validate()

    geometry_file = writer.write_block4_fragment(
        OUTPUT_DIR / "geometry_material.inc"
    )
    quadrature_file = quadrature.write_dort(OUTPUT_DIR / "quadrature_s8.inc")
    control_file = OUTPUT_DIR / "run_control.inc"
    control_file.write_text(run.control_fragment() + "\n", encoding="ascii")
    neutron_shape = np.geomspace(1.0, 1.0e-3, 175)
    array1 = np.concatenate((neutron_shape / neutron_shape.sum(), np.zeros(42)))
    deck_file = writer.write_complete_input(
        OUTPUT_DIR / "dortinp_rerun.inp",
        run_control=run, quadrature=quadrature, array1=array1,
        title="Tutorial eigenvalue restart input",
    )

    # Restart mode reads the flux from unit 20, so cards 93*--98* are neither
    # required nor permitted for this calculation profile.
    card_check = run.validate_present_cards(())
    if not card_check.valid:
        raise RuntimeError(card_check.summary_text())

    print(run.summary_text())
    print("\nFILE UNITS")
    print(run.file_units)
    print("\nOPTIONAL CARD POLICY")
    print(run.card_policy.summary_text())

    previous_flux = OUTPUT_DIR / run.output_flux_filename
    if previous_flux.exists():
        guess_flux = run.prepare_rerun_flux(OUTPUT_DIR, overwrite=True)
        print(f"\nPrepared restart input: {guess_flux}")
    else:
        print("\nRESTART FILE NOT COPIED")
        print(f"Place the previous unformatted flux at: {previous_flux}")
        print("Run the example again to create guessflux.bin for unit 20.")

    print("\nFILES")
    print(f"{'geometry':16s}: {geometry_file}")
    print(f"{'quadrature':16s}: {quadrature_file}")
    print(f"{'run control':16s}: {control_file}")
    print(f"{'combined input':16s}: {deck_file}")


if __name__ == "__main__":
    main()
