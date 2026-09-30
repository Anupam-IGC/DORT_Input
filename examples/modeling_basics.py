"""Tutorial 1: build, inspect, and serialize a complete R-Z model.

This is the best example to copy when starting a new model. It demonstrates
the recommended order of work:

1. load material mixtures;
2. define the R and Z mesh;
3. set a background material and add regions;
4. build and inspect the final cell assignments;
5. create a DORT writer and write geometry/material cards.

Run from the repository root with::

    python examples/modeling_basics.py
"""

from pathlib import Path

from dort_input import DORTModel, DORTWriter
from dort_input.plotting import (
    save_material_plot, save_material_region_union_plot, save_region_plot,
    write_outline_csv,
)


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "examples" / "data" / "mixtures_example.xlsx"
DEFAULT_OUTPUT = ROOT / "example_output" / "01_modeling_basics"


def build_sample_model() -> DORTModel:
    """Return the validated model shared by the remaining tutorials."""
    model = DORTModel("tutorial_shielding_model")

    # Load mixtures before defining any regions. Workbook-column order fixes
    # the natural material IDs and the corresponding mixf.cr table sequence.
    model.load_mixtures_from_excel(
        WORKBOOK,
        legendre_order=5,
    )

    # Piecewise mesh segments let important interfaces use finer cells.
    model.mesh.r.add_segment(0.0, 40.0, step=5.0)
    model.mesh.r.add_segment(40.0, 50.0, step=2.0)
    model.mesh.r.add_segment(50.0, 80.0, step=5.0)
    model.mesh.r.add_segment(80.0, 100.0, step=10.0)

    model.mesh.z.add_segment(-100.0, -60.0, step=10.0)
    model.mesh.z.add_segment(-60.0, 60.0, step=5.0)
    model.mesh.z.add_segment(60.0, 100.0, step=10.0)

    # The background fills every cell not claimed by a higher-priority region.
    model.set_background("Sodium")

    model.add_region(
        "central_block",
        material="Graphite",
        r=(0.0, 40.0),
        z=(-40.0, 40.0),
        priority=20,
    )
    model.add_region(
        "gas_plenum",
        material="Argon",
        r=(0.0, 40.0),
        z=(40.0, 60.0),
        priority=20,
    )
    model.add_region(
        "steel_vessel",
        material="Carbon Steel",
        r=(40.0, 50.0),
        z=(-60.0, 60.0),
        priority=30,
    )
    model.add_region(
        "b4c_shield",
        material="B4C Powder",
        r=(50.0, 80.0),
        z=(-60.0, 60.0),
        priority=30,
    )

    # This small window deliberately overlaps the shield and wins because its
    # priority is higher. Equal-priority overlaps are rejected by the builder.
    model.add_region(
        "lead_window",
        material="Lead",
        r=(60.0, 80.0),
        z=(-10.0, 10.0),
        priority=50,
    )

    model.build(strict_region_bounds=True)
    return model


def main() -> None:
    output_dir = DEFAULT_OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)

    model = build_sample_model()

    # These files are inputs and mapping aids for the external mixer workflow.
    mixture_files = model.write_mixture_preparation_files(output_dir / "mixtures")

    # One zone per material keeps 9$$ and the 62$$ IZM count aligned with the
    # used mixture table; region ownership remains available in the model.
    writer = DORTWriter(
        model,
        zone_policy="material",
        cross_section_unit=51,
        cross_section_filename="mixf.cr",
    )
    geometry_file = writer.write_block4_fragment(
        output_dir / "geometry_material.inc"
    )

    # Visual inspection should be part of every production model review.
    save_material_plot(model, output_dir / "materials.png", show_mesh=True)
    save_region_plot(model, output_dir / "regions.png", show_mesh=True)
    save_material_region_union_plot(model, output_dir / "material_region_union.png")
    write_outline_csv(model, output_dir / "geometry_outlines.csv")

    # Inspect just the shielding layers. Interfaces are drawn on mesh edges,
    # and each visible connected area gets one material ID label.
    detail = dict(r_extent=(35.0, 85.0), z_extent=(-30.0, 30.0))
    save_material_plot(
        model, output_dir / "material_detail.png", **detail,
        show_material_boundaries=True, show_material_ids=True,
    )
    save_region_plot(model, output_dir / "region_detail.png", **detail)
    save_material_plot(
        model, output_dir / "material_outline.png", **detail,
        color_fill=False,
    )

    print(model)
    print("\nMATERIAL CELL COUNTS")
    print(model.material_cell_counts())
    print("\nREGION CELL COUNTS")
    print(model.region_cell_counts())
    print("\nSAMPLE CELL (CENTRAL BLOCK)")
    print(
        model.cell_assignment(
            z_index=model.mesh.z.n_cells // 2,
            r_index=0,
        )
    )
    print("\nMATERIAL TABLE MAPPING")
    print(writer.material_layout_text())
    print("\nDORT ZONES")
    print(writer.zone_table_text())

    print("\nFILES")
    for label, path in mixture_files.items():
        print(f"{label:16s}: {path}")
    print(f"{'geometry':16s}: {geometry_file}")
    print(f"{'material plot':16s}: {output_dir / 'materials.png'}")
    print(f"{'region plot':16s}: {output_dir / 'regions.png'}")
    print(f"{'union plot':16s}: {output_dir / 'material_region_union.png'}")
    print(f"{'outline CSV':16s}: {output_dir / 'geometry_outlines.csv'}")
    print(f"{'material detail':16s}: {output_dir / 'material_detail.png'}")
    print(f"{'region detail':16s}: {output_dir / 'region_detail.png'}")
    print(f"{'material outline':16s}: {output_dir / 'material_outline.png'}")


if __name__ == "__main__":
    main()
