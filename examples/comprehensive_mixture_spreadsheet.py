"""Comprehensive spreadsheet-driven external-mixture workflow.

This example uses the same workbook layout as the supplied ``mixture.py``:

    Nuclide | MAT No. | Mixture A | Mixture B | ...

Nonblank cells under a mixture are atom densities.  Mixture IDs follow the
left-to-right workbook column order.

Run from the repository root::

    python examples/comprehensive_mixture_spreadsheet.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import DORTModel
from writer import DORTWriter


def main() -> None:
    workbook = ROOT / "examples" / "data" / "mixtures_example.xlsx"
    output_dir = ROOT / "example_output" / "mixture_spreadsheet"
    output_dir.mkdir(parents=True, exist_ok=True)

    model = DORTModel("spreadsheet_mixture_demo")

    # Recommended path: one call imports the workbook in column order and writes
    # mix.inp, Mixture_Names.txt, and the compact material-policy mapping cards.
    files = model.prepare_mixtures_from_excel(
        workbook,
        sheet_name="Read",
        legendre_order=5,
        output_dir=output_dir,
    )

    print("REGISTERED MIXTURES")
    print(model.mixtures.layout_text(model.materials.legendre_order))
    print()
    for label, path in files.items():
        print(f"{label:14s}: {path}")

    # The sample workbook defines: Sodium, Argon, Graphite, Lead, B4C Powder,
    # and Carbon Steel.  These names can immediately be used in geometry.
    model.mesh.r.add_segment(0.0, 40.0, step=5.0)
    model.mesh.r.add_segment(40.0, 80.0, step=5.0)
    model.mesh.z.add_segment(-50.0, 0.0, step=5.0)
    model.mesh.z.add_segment(0.0, 50.0, step=5.0)

    model.set_background("Sodium")
    model.add_region(
        "graphite_block",
        material="Graphite",
        r=(0.0, 30.0),
        z=(-20.0, 20.0),
        priority=20,
    )
    model.add_region(
        "steel_shell",
        material="Carbon Steel",
        r=(30.0, 50.0),
        z=(-30.0, 30.0),
        priority=30,
    )
    model.add_region(
        "b4c_insert",
        material="B4C Powder",
        r=(0.0, 15.0),
        z=(-10.0, 10.0),
        priority=40,
    )
    model.build()

    # Region-zone mode may create more zones than mixtures.  In that case use
    # the writer's zone-aware cards instead of the compact spreadsheet cards.
    writer = DORTWriter(model, zone_policy="region", cross_section_unit=51)
    writer.write_mixture_cards(output_dir / "dort_mix_cards_zone_aware.txt")
    writer.write_block4_fragment(output_dir / "geometry_material.inc")

    print("\nZONE-AWARE MAPPING")
    print(writer.zone_table_text())
    print("\n9$$ card")
    print(writer.array9())
    print("\n84$$ by material")
    print(writer.array84_by_material())


if __name__ == "__main__":
    main()
