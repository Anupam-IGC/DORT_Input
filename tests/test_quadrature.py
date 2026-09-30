import numpy as np

from dort_input import (
    generate_legacy_quadrature,
    generate_product_quadrature,
)


def test_legacy_s8_matches_reference() -> None:
    quadrature = generate_legacy_quadrature(
        order=8,
        symmetry="half",
    )

    expected_radial = np.array([
        -0.308607,
        -0.218218,
         0.218218,
        -0.617213,
        -0.577350,
        -0.218218,
         0.218218,
         0.577350,
    ])

    expected_axial = np.array([
        -0.951190,
        -0.951190,
        -0.951190,
        -0.786796,
        -0.786796,
        -0.786796,
        -0.786796,
        -0.786796,
    ])

    expected_weights = np.array([
        0.0,
        0.0302469,
        0.0302469,
        0.0,
        0.0226852,
        0.0226852,
        0.0226852,
        0.0226852,
    ])

    np.testing.assert_allclose(
        quadrature.radial_cosine[:8],
        expected_radial,
        atol=5e-7,
    )
    np.testing.assert_allclose(
        quadrature.axial_cosine[:8],
        expected_axial,
        atol=5e-7,
    )
    np.testing.assert_allclose(
        quadrature.weights[:8],
        expected_weights,
        atol=5e-8,
    )

    assert quadrature.direction_count == 48
    assert quadrature.zero_weight_direction_count == 8
    assert np.isclose(quadrature.weight_sum, 1.0)
    assert quadrature.validate(
        require_positive_weights=False
    ).valid


def test_product_24x32_is_positive_and_valid() -> None:
    quadrature = generate_product_quadrature(
        polar_order=24,
        azimuthal_order=32,
    )

    report = quadrature.validate()

    assert report.valid
    assert report.minimum_nonzero_weight > 0.0
    assert quadrature.direction_count == 24 * 33
    assert np.isclose(quadrature.weight_sum, 1.0)
    assert report.maximum_level_current < 1e-12
    assert report.maximum_moment_error < 1e-12


def test_product_64x64_stress_case() -> None:
    quadrature = generate_product_quadrature(
        polar_order=64,
        azimuthal_order=64,
    )

    report = quadrature.validate()

    assert report.valid
    assert report.minimum_nonzero_weight > 0.0
    assert quadrature.direction_count == 64 * 65
    assert report.maximum_moment_error < 1e-12


def test_dort_output_contains_all_arrays() -> None:
    quadrature = generate_product_quadrature(
        polar_order=8,
        azimuthal_order=8,
    )

    text = quadrature.dort_text()

    assert "82**" in text
    assert "83**" in text
    assert "81**" in text


def test_s16_half_quadrature_has_exactly_mm_fields_per_array() -> None:
    quadrature = generate_legacy_quadrature(order=16, symmetry="half")
    text = quadrature.dort_text()
    arrays = {
        82: text.split("82**", 1)[1].split("83**", 1)[0],
        83: text.split("83**", 1)[1].split("81**", 1)[0],
        81: text.split("81**", 1)[1],
    }
    assert quadrature.direction_count == 160
    for array in arrays.values():
        fields = array.split()
        assert len(fields) == 160
        assert all(field.lower() not in {"t", "e"} for field in fields)
        for field in fields:
            float(field)
    assert max(map(len, text.splitlines())) <= 72
