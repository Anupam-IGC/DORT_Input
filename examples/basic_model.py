"""
End-to-end example for the DORT R-Z input preparation API.

Run from the repository root:

    python examples/basic_model.py
"""

from pathlib import Path
import sys

# Allow this example to run directly from the examples/ directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import DORTModel
from plotting import save_material_plot, save_region_plot
from writer import DORTWriter


def main() -> None:
    output_dir = ROOT / "example_output"
    output_dir.mkdir(exist_ok=True)

    model = DORTModel("basic_RZ_example")

    # ------------------------------------------------------------
    # Materials
    # ------------------------------------------------------------
    for name in ("Sodium", "Core", "SS316", "B4C", "Air"):
        model.add_material(name)

    # ------------------------------------------------------------
    # Mesh
    # ------------------------------------------------------------
    model.mesh.r.add_segment(0.0, 100.0, step=5.0)
    model.mesh.r.add_segment(100.0, 140.0, step=2.0)
    model.mesh.r.add_segment(140.0, 200.0, step=5.0)

    model.mesh.z.add_segment(-100.0, -50.0, step=5.0)
    model.mesh.z.add_segment(-50.0, 50.0, step=2.0)
    model.mesh.z.add_segment(50.0, 100.0, step=5.0)

    # ------------------------------------------------------------
    # Background + regions
    # ------------------------------------------------------------
    model.set_background("Sodium")

    model.add_region(
        "core",
        material="Core",
        r=(0.0, 100.0),
        z=(-50.0, 50.0),
        priority=20,
    )

    model.add_region(
        "radial_shield",
        material="SS316",
        r=(100.0, 140.0),
        z=(-50.0, 50.0),
        priority=30,
    )

    model.add_region(
        "bottom_shield",
        material="B4C",
        r=(0.0, 140.0),
        z=(-100.0, -50.0),
        priority=30,
    )

    model.add_region(
        "penetration",
        material="Air",
        r=(80.0, 120.0),
        z=(-10.0, 10.0),
        priority=50,
    )

    # ------------------------------------------------------------
    # Build
    # ------------------------------------------------------------
    summary = model.build()
    print(summary)

    if summary.warnings:
        print("\nWarnings:")
        for warning in summary.warnings:
            print(" -", warning)

    print("\nMaterial cell counts:")
    for name, count in model.material_cell_counts().items():
        print(f"  {name:16s}: {count}")

    print("\nRegion cell counts:")
    for name, count in model.region_cell_counts().items():
        print(f"  {name:16s}: {count}")

    # ------------------------------------------------------------
    # Visual verification
    # ------------------------------------------------------------
    save_material_plot(
        model,
        output_dir / "material_map.png",
        show_mesh=True,
    )

    save_region_plot(
        model,
        output_dir / "region_map.png",
        show_mesh=True,
    )

    # ------------------------------------------------------------
    # DORT writer
    # ------------------------------------------------------------
    writer = DORTWriter(
        model,
        zone_policy="region",
        # Replace these examples with the actual identifiers used
        # by your DORT/GIP cross-section library.
        material_numbers={
            "Core": -1,
            "Sodium": -169,
            "SS316": -145,
            "B4C": -181,
            "Air": -117,
        },
    )

    print("\n" + writer.summary_text())

    writer.write_block4_fragment(
        output_dir / "geometry_material_fragment.inp"
    )

    (output_dir / "writer_summary.txt").write_text(
        writer.summary_text() + "\n",
        encoding="utf-8",
    )

    print(f"\nOutput written to: {output_dir}")


if __name__ == "__main__":
    main()
