"""Comprehensive quadrature generation/validation example.

Run from the repository root:

    python examples/comprehensive_quadrature.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quadrature import generate_legacy_quadrature, generate_product_quadrature
from quadrature_plotting import plot_quadrature_set


def main() -> None:
    output_dir = ROOT / "example_output" / "quadrature"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Conventional legacy set for reproducing established calculations.
    legacy = generate_legacy_quadrature(order=8, symmetry="half")
    print("LEGACY S8")
    print(legacy.summary_text())
    print(legacy.validation_text())
    legacy.write_dort(output_dir / "legacy_s8.inc")

    fig, _ = plot_quadrature_set(
        legacy,
        display_mode="scatter",
        scale_markers_by_weight=True,
    )
    fig.savefig(output_dir / "legacy_s8.png", dpi=180, bbox_inches="tight")

    # Positive-weight product quadrature for higher angular resolution.
    product = generate_product_quadrature(
        polar_order=24,
        azimuthal_order=32,
    )
    print("\nPRODUCT 24 x 32")
    print(product.summary_text())
    print(product.validation_text())
    product.write_dort(output_dir / "product_24x32.inc")

    fig, _ = plot_quadrature_set(
        product,
        display_mode="auto",
        scale_markers_by_weight=True,
    )
    fig.savefig(output_dir / "product_24x32.png", dpi=180, bbox_inches="tight")

    print(f"\nFiles written to {output_dir}")


if __name__ == "__main__":
    main()
