"""Regressions against the supplied DORT card conventions and plotting."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from dort_input import DORTModel, DORTWriter, generate_product_quadrature
from dort_input.mixtures import MixtureRegistry
from dort_input.quadrature_plotting import plot_quadrature_3d, plot_quadrature_set


def sample_writer():
    model = DORTModel("ordering")
    for name, mat in (("A", 1), ("B", 2), ("C", 3)):
        model.add_mixture(name, {mat: 0.01}, legendre_order=5)
    model.mesh.r.add_segment(0, 3, step=1)
    model.mesh.z.add_segment(0, 1, step=1)
    model.set_background("A")
    model.add_region("c_first", material="C", r=(0, 1), z=(0, 1))
    model.add_region("b_second", material="B", r=(1, 2), z=(0, 1))
    model.build()
    return DORTWriter(model, zone_policy="region")


def test_geometry_9_card_tracks_zone_ids_in_mixture_order():
    writer = sample_writer()
    assert [zone.material for zone in writer.zones] == ["A", "B", "C"]
    assert writer.array9() == "9$$ -1 -7 -13 t"
    # Cell 0 belongs to C despite its zone being number 3.
    assert writer.zone_map[0, 0] == 3
    assert writer.zone_map[0, 1] == 2
    assert writer.block4_geometry_material_fragment().endswith("9$$ -1 -7 -13 t")


def test_uniform_initial_flux_matches_supplied_deck_and_restart_omits_it():
    writer = sample_writer()
    initial = writer.create_run_control(
        "eigenvalue_first", energy_groups=4, quadrature_directions=48
    )
    cards = initial.initial_flux_fragment()
    assert cards == "93** F 1.0 t\n94** F 1.0 t\n95** F 1.0 t"
    assert initial.control_and_initial_flux_fragment().endswith(cards)
    assert initial.initial_flux_fragment(value=2.0) == (
        "93** F 2.0 t\n94** F 2.0 t\n95** F 2.0 t"
    )
    rerun = writer.create_run_control(
        "eigenvalue_rerun", energy_groups=4, quadrature_directions=48
    )
    assert rerun.initial_flux_fragment() == ""


def test_first_workbook_sheet_is_selected_without_a_name(tmp_path):
    workbook = tmp_path / "mixtures.xlsx"
    with pd.ExcelWriter(workbook) as excel:
        pd.DataFrame({"Nuclide": ["iron"], "MAT No.": [26056], "steel": [0.01]}).to_excel(
            excel, sheet_name="Materials", index=False
        )
        pd.DataFrame({"Nuclide": ["argon"], "MAT No.": [18040], "gas": [0.02]}).to_excel(
            excel, sheet_name="Other", index=False
        )
    assert MixtureRegistry.from_excel(workbook).names == ("steel",)
    assert MixtureRegistry.from_excel(workbook, sheet_name="Other").names == ("gas",)


@pytest.mark.parametrize("direction", ("+z", "-z", "+r", "-r"))
def test_biased_quadrature_keeps_isotropic_measure(direction):
    q = generate_product_quadrature(
        polar_order=24, azimuthal_order=32,
        bias_direction=direction, bias_fraction=0.75,
    )
    assert q.direction_count == 24 * 33
    assert q.validate().valid
    assert q.maximum_moment_error < 1e-8
    assert "81**" in q.dort_text()
    positive_axial_levels = np.count_nonzero(np.unique(q.axial_cosine) > 0)
    if direction == "+z":
        assert positive_axial_levels == 18
    if direction == "-z":
        assert positive_axial_levels == 6
    if direction in ("+r", "-r"):
        # Skip the zero-weight initiators when measuring node concentration.
        selected = q.radial_cosine[q.weights > 0]
        assert np.count_nonzero(selected * (1 if direction == "+r" else -1) > 0) == 24 * 24


def test_3d_plot_shows_first_octant_sphere_with_weight_scaled_points():
    q = generate_product_quadrature(polar_order=16, azimuthal_order=16)
    fig, ax = plot_quadrature_3d(q)
    try:
        x, y, z = ax.collections[0]._offsets3d
        np.testing.assert_allclose(np.asarray(x)**2 + np.asarray(y)**2 + np.asarray(z)**2, 1)
        assert np.all(np.asarray(x) >= 0) and np.all(np.asarray(z) >= 0)
        assert len(np.unique(ax.collections[0].get_sizes())) > 2
        assert ax.get_legend() is None
    finally:
        plt.close(fig)
    fig, ax = plot_quadrature_set(q)
    try:
        assert hasattr(ax, "zaxis")  # the convenient default is also 3-D
    finally:
        plt.close(fig)
