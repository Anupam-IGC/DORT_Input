"""Comprehensive geometry/material/zone example.

Run from the repository root:

    python examples/comprehensive_geometry.py

Outputs are written to ``example_output/geometry``.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import DORTModel
from plotting import plot_materials, plot_regions
from writer import DORTWriter


def main() -> None:
    output_dir = ROOT / "example_output" / "geometry"
    output_dir.mkdir(parents=True, exist_ok=True)

    model = DORTModel("geometry_demo")

    # Geometry-only material labels.  All materials use the same P5 order.
    for name in ("Coolant", "Core", "Steel", "Shield"):
        model.add_material(name, legendre_order=5)

    # Piecewise radial mesh: coarse outside, finer near the central system.
    model.mesh.r.add_segment(0.0, 80.0, step=5.0)
    model.mesh.r.add_segment(80.0, 120.0, step=2.0)
    model.mesh.r.add_segment(120.0, 180.0, step=10.0)

    # Negative Z is valid in R-Z geometry; only R is restricted to R >= 0.
    model.mesh.z.add_segment(-100.0, -50.0, step=10.0)
    model.mesh.z.add_segment(-50.0, 50.0, step=5.0)
    model.mesh.z.add_segment(50.0, 100.0, step=10.0)

    model.set_background("Coolant")

    # Lower priority central region.
    model.add_region(
        "core",
        material="Core",
        r=(0.0, 80.0),
        z=(-50.0, 50.0),
        priority=20,
    )

    # Higher-priority radial shield.
    model.add_region(
        "radial_shield",
        material="Steel",
        r=(80.0, 120.0),
        z=(-60.0, 60.0),
        priority=30,
    )

    # Axial shields.
    model.add_region(
        "lower_shield",
        material="Shield",
        r=(0.0, 120.0),
        z=(-100.0, -50.0),
        priority=30,
    )
    model.add_region(
        "upper_shield",
        material="Shield",
        r=(0.0, 120.0),
        z=(50.0, 100.0),
        priority=30,
    )

    # A penetration deliberately overlaps other regions and wins by priority.
    model.add_region(
        "penetration",
        material="Coolant",
        r=(60.0, 100.0),
        z=(-10.0, 10.0),
        priority=50,
    )

    summary = model.build()
    print(summary)
    print("Material cell counts:", model.material_cell_counts())
    print("Region cell counts  :", model.region_cell_counts())

    # Visual checks should be routine before exporting a production model.
    fig, _ = plot_materials(model, show_mesh=True)
    fig.savefig(output_dir / "materials.png", dpi=180, bbox_inches="tight")

    fig, _ = plot_regions(model, show_mesh=True)
    fig.savefig(output_dir / "regions.png", dpi=180, bbox_inches="tight")

    # Here we use simple positive material numbers only to demonstrate geometry
    # serialization without the external mixture workflow.
    writer = DORTWriter(
        model,
        zone_policy="region",
        material_numbers={
            "Coolant": 1,
            "Core": 2,
            "Steel": 3,
            "Shield": 4,
        },
    )

    print("\nWRITER SUMMARY")
    print(writer.summary_text())
    print("\nZONE TABLE")
    print(writer.zone_table_text())

    writer.write_block4_fragment(output_dir / "geometry_material.inc")
    (output_dir / "edit_regions.inc").write_text(
        writer.array84_identity() + "\n",
        encoding="utf-8",
    )

    print(f"\nFiles written to {output_dir}")


if __name__ == "__main__":
    main()
