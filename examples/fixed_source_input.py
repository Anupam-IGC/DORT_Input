"""Tutorial 3: prepare a complete mesh-based fixed-source fragment.

The spectrum used here is synthetic and only demonstrates data flow. Replace
it with a physically justified group spectrum for an actual calculation.

Run from the repository root with::

    python examples/fixed_source_input.py
"""

import matplotlib.pyplot as plt
import numpy as np

from dort_input import DORTWriter, generate_legacy_quadrature

from modeling_basics import ROOT, build_sample_model


OUTPUT_DIR = ROOT / "example_output" / "03_fixed_source_input"


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

    # Construct the 96** spatial field using the same named geometry that was
    # already reviewed in the model plots.
    source = writer.create_source(background=0.0)
    source.by_region("central_block", strength=1.0)
    source.by_material("B4C Powder", strength=0.05, combine="add")
    source.by_mesh(
        r=(10.0, 20.0),
        z=(-10.0, 10.0),
        strength=0.25,
        combine="add",
    )

    # Illustrative 217-group energy shape for card 98**.
    spectrum = np.geomspace(1.0, 1.0e-4, 217)
    source.set_energy_spectrum(spectrum, normalize=True)

    quadrature = generate_legacy_quadrature(order=8, symmetry="half")
    run = writer.create_run_control(
        "fixed_source",
        energy_groups=217,
        quadrature_directions=quadrature.direction_count,
        neutron_groups=175,
        starting_flux="zero",
        maximum_outer_iterations=20,
        initial_inner_iterations=30,
        final_inner_iterations=20,
        left_boundary="reflected",
        right_boundary="void",
        bottom_boundary="void",
        top_boundary="void",
        scalar_flux_printing="none",
        cross_section_printing="suppress",
    )
    run.attach_source(source)
    run.validate()

    geometry_file = writer.write_block4_fragment(
        OUTPUT_DIR / "geometry_material.inc"
    )
    quadrature_file = quadrature.write_dort(OUTPUT_DIR / "quadrature_s8.inc")
    source_file = OUTPUT_DIR / "run_control_and_source.inc"
    source_file.write_text(
        run.control_and_source_fragment() + "\n",
        encoding="ascii",
    )
    deck_file = writer.write_complete_input(
        OUTPUT_DIR / "dortinp_fixed.inp",
        run_control=run, quadrature=quadrature,
        array1=np.zeros(217), title="Tutorial fixed-source input",
    )

    # With a zero starting flux, only cards 96** and 98** are required from the
    # optional 93*--98* group. This check catches accidental card mismatches.
    card_check = run.validate_present_cards((96, 98))
    if not card_check.valid:
        raise RuntimeError(card_check.summary_text())

    fig, ax = plt.subplots()
    image = ax.pcolormesh(
        model.mesh.r.edges,
        model.mesh.z.edges,
        source.spatial,
        shading="flat",
    )
    ax.set_xlabel("R")
    ax.set_ylabel("Z")
    ax.set_title("Tutorial fixed-source spatial field")
    fig.colorbar(image, ax=ax, label="Relative source strength")
    fig.savefig(OUTPUT_DIR / "source_spatial.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(source.summary_text())
    print("\nRUN MODE")
    print(run.summary_text())
    print("\nOPTIONAL CARD POLICY")
    print(run.card_policy.summary_text())

    print("\nFILES")
    for label, path in mixture_files.items():
        print(f"{label:16s}: {path}")
    print(f"{'geometry':16s}: {geometry_file}")
    print(f"{'quadrature':16s}: {quadrature_file}")
    print(f"{'control/source':16s}: {source_file}")
    print(f"{'combined input':16s}: {deck_file}")
    print(f"{'source plot':16s}: {OUTPUT_DIR / 'source_spatial.png'}")

    print("\nReplace the synthetic spectrum before using these cards in a")
    print("physical shielding calculation.")


if __name__ == "__main__":
    main()
