"""Comprehensive fixed-source workflow.

This example demonstrates source selection from existing geometry, a separate
energy-spectrum file, source-card generation, run controls, quadrature, and a
quick spatial-source plot.

Run from the repository root:

    python examples/comprehensive_fixed_source.py
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import DORTModel
from quadrature import generate_legacy_quadrature
from writer import DORTWriter


def build_model() -> DORTModel:
    model = DORTModel("fixed_source_demo")
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
    output_dir = ROOT / "example_output" / "fixed_source"
    output_dir.mkdir(parents=True, exist_ok=True)

    model = build_model()
    writer = DORTWriter(model, zone_policy="region", cross_section_unit=51)

    # Start with a tiny nonzero floor if that is useful for the local solver.
    source = writer.create_source(background=1.0e-20)

    # Main source follows an already-defined physical region.
    source.by_region("central_region", strength=1.0)

    # Add a weaker contribution in another region.
    source.by_region("radial_shield", strength=0.15, combine="add")

    # Superimpose a local hot spot using mesh-cell centres.
    source.by_mesh(
        r=(0.0, 20.0),
        z=(-15.0, 15.0),
        strength=0.25,
        combine="add",
    )

    # Create an *illustrative* 217-group spectrum file. Replace this synthetic
    # spectrum by the physical spectrum for a real calculation.
    spectrum_file = output_dir / "source_spectrum_217g.txt"
    x = np.linspace(0.0, 6.0, 217)
    illustrative_spectrum = np.exp(-x)
    np.savetxt(spectrum_file, illustrative_spectrum, fmt="%.12E")

    source.set_energy_spectrum_file(spectrum_file, normalize=True)
    print(source.summary_text())

    quadrature = generate_legacy_quadrature(order=8, symmetry="half")

    run = writer.create_run_control(
        "fixed_source",
        energy_groups=217,
        quadrature_directions=quadrature.direction_count,
        neutron_groups=175,
        maximum_outer_iterations=20,
        left_boundary="reflected",
        right_boundary="void",
        scalar_flux_printing="none",
        cross_section_printing="suppress",
    )
    run.attach_source(source)

    writer.write_block4_fragment(output_dir / "geometry_material.inc")
    quadrature.write_dort(output_dir / "quadrature_s8.inc")
    (output_dir / "run_control_and_source.inc").write_text(
        run.control_and_source_fragment() + "\n",
        encoding="utf-8",
    )

    # Simple visual inspection of the generated 96** spatial field.
    fig, ax = plt.subplots()
    mesh = ax.pcolormesh(
        model.mesh.r.edges,
        model.mesh.z.edges,
        source.spatial,
        shading="flat",
    )
    ax.set_xlabel("R")
    ax.set_ylabel("Z")
    ax.set_title("Fixed-source spatial field")
    fig.colorbar(mesh, ax=ax, label="Relative source strength")
    fig.savefig(output_dir / "spatial_source.png", dpi=180, bbox_inches="tight")

    print("\nCARD POLICY")
    print(run.card_policy.summary_text())
    print(f"\nFiles written to {output_dir}")


if __name__ == "__main__":
    main()
