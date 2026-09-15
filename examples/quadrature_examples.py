"""
Examples for the modern DORT quadrature API.

Run from the repository root:

    python examples/quadrature_examples.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quadrature import (
    generate_legacy_quadrature,
    generate_product_quadrature,
)


def main() -> None:
    output_dir = ROOT / "quadrature_output"
    output_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------------
    # 1. Legacy S8 set
    # ------------------------------------------------------------
    legacy = generate_legacy_quadrature(
        order=8,
        symmetry="half",
    )

    print("LEGACY S8")
    print(legacy.summary_text())
    print()
    print(legacy.validation_text())

    legacy.write_dort(
        output_dir / "legacy_s8.inc"
    )

    # ------------------------------------------------------------
    # 2. Modern high-order product set
    # ------------------------------------------------------------
    product = generate_product_quadrature(
        polar_order=24,
        azimuthal_order=32,
    )

    print("\nPRODUCT 24 x 32")
    print(product.summary_text())
    print()
    print(product.validation_text())

    product.write_dort(
        output_dir / "product_24x32.inc"
    )

    print(f"\nFiles written to {output_dir}")


if __name__ == "__main__":
    main()
