"""Tutorial 5: compare established and alternative quadrature sets.

Use an alternative quadrature in production only after confirming that the
local DORT executable accepts its direction ordering and reproduces trusted
reference calculations.

Run from the repository root with::

    python examples/quadrature_comparison.py
"""

from dort_input import generate_legacy_quadrature, generate_product_quadrature
from dort_input.quadrature_plotting import (
    save_quadrature_3d_plot,
)

from modeling_basics import ROOT


OUTPUT_DIR = ROOT / "example_output" / "05_quadrature_comparison"


def validate_and_write(name, quadrature) -> None:
    report = quadrature.validate(
        require_positive_weights=quadrature.family != "legacy"
    )
    if not report.valid:
        raise RuntimeError(report.text())

    quadrature.write_dort(OUTPUT_DIR / f"{name}.inc")
    save_quadrature_3d_plot(quadrature, OUTPUT_DIR / f"{name}_directions.png")

    print(f"\n{name.upper()}")
    print(quadrature.summary_text())
    print(report.text())


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    legacy = generate_legacy_quadrature(order=8, symmetry="half")
    product = generate_product_quadrature(
        polar_order=16,
        azimuthal_order=16,
    )
    biased = generate_product_quadrature(
        polar_order=24,
        azimuthal_order=32,
        bias_direction="+z",
        bias_fraction=0.75,
    )

    validate_and_write("legacy_s8", legacy)
    validate_and_write("product_16x16", product)
    validate_and_write("product_biased_positive_z", biased)

    print(f"\nFiles written to {OUTPUT_DIR}")
    print("Keep the legacy set as the production baseline until an alternative")
    print("has passed solver-level benchmark and sensitivity checks.")


if __name__ == "__main__":
    main()
