"""
quadrature_plotting.py
======================

Visualization helpers for DORT quadrature sets.

This module adds multiple plotting styles because a simple cosine-plane
scatter plot becomes crowded for larger quadrature sets.  In particular,
high-order product quadratures can have many points lying on closely spaced
axial-cosine levels, so an ordinary scatter plot can become visually dense.

Provided plotting styles
------------------------
1. ``display_mode="scatter"``
   Standard plot in the (radial cosine, axial cosine) plane.

2. ``display_mode="jittered"``
   Same plane, but each axial-cosine level is given a small display-only
   vertical spread to reduce marker overlap.

3. ``display_mode="indexed_levels"``
   Uses level index on the vertical axis instead of the physical axial cosine.
   This is often the clearest representation for large quadrature sets.

Typical usage
-------------
.. code-block:: python

   from quadrature import generate_product_quadrature
   from quadrature_plotting import plot_quadrature_set

   quadrature = generate_product_quadrature(
       polar_order=24,
       azimuthal_order=32,
   )

   fig, ax = plot_quadrature_set(
       quadrature,
       display_mode="indexed_levels",
       scale_markers_by_weight=True,
   )

   fig.savefig(
       "quadrature_distribution.png",
       dpi=200,
       bbox_inches="tight",
   )
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from quadrature import QuadratureSet


def _marker_sizes_from_weights(
    weights: np.ndarray,
    *,
    minimum_size: float = 18.0,
    maximum_size: float = 140.0,
) -> np.ndarray:
    """
    Convert directional weights into visually useful scatter-marker sizes.

    A square-root scaling is used so that a few larger weights do not dominate
    the plot while smaller weights remain visible.
    """
    weights = np.asarray(weights, dtype=float)

    if weights.ndim != 1:
        raise ValueError("weights must be a one-dimensional array.")

    positive = weights > 0.0

    if not np.any(positive):
        return np.full(weights.shape, minimum_size, dtype=float)

    maximum_weight = float(np.max(weights[positive]))

    if maximum_weight <= 0.0:
        return np.full(weights.shape, minimum_size, dtype=float)

    scaled = np.sqrt(np.clip(weights / maximum_weight, 0.0, None))
    return minimum_size + (maximum_size - minimum_size) * scaled


def _find_level_slices(
    axial_cosine: np.ndarray,
    *,
    tolerance: float = 1.0e-12,
) -> list[slice]:
    if axial_cosine.size == 0:
        return []

    starts = [0]

    for index in range(1, axial_cosine.size):
        if not np.isclose(
            axial_cosine[index],
            axial_cosine[index - 1],
            atol=tolerance,
            rtol=0.0,
        ):
            starts.append(index)

    slices: list[slice] = []

    for idx, start in enumerate(starts):
        stop = starts[idx + 1] if idx + 1 < len(starts) else axial_cosine.size
        slices.append(slice(start, stop))

    return slices


def _build_display_coordinates(
    quadrature: QuadratureSet,
    *,
    display_mode: str,
    jitter_fraction: float,
) -> tuple[np.ndarray, np.ndarray, str]:
    """
    Return display coordinates for the selected plot mode.
    """
    radial = np.asarray(quadrature.radial_cosine, dtype=float)
    axial = np.asarray(quadrature.axial_cosine, dtype=float)
    level_slices = _find_level_slices(axial)

    normalized_mode = str(display_mode).strip().lower()

    if normalized_mode == "auto":
        if quadrature.direction_count <= 200:
            normalized_mode = "scatter"
        elif quadrature.direction_count <= 1000:
            normalized_mode = "jittered"
        else:
            normalized_mode = "indexed_levels"

    if normalized_mode == "scatter":
        return radial.copy(), axial.copy(), normalized_mode

    if normalized_mode == "jittered":
        y = axial.copy()

        if not (0.0 <= jitter_fraction <= 1.0):
            raise ValueError("jitter_fraction must lie between 0 and 1.")

        if level_slices:
            unique_levels = np.array([axial[level.start] for level in level_slices], dtype=float)

            if unique_levels.size > 1:
                # Half the minimum gap between actual levels times the user factor.
                min_spacing = float(np.min(np.diff(np.sort(unique_levels))))
                half_spread = 0.5 * jitter_fraction * min_spacing
            else:
                half_spread = 0.04 * max(1.0, float(np.max(np.abs(unique_levels))))

            for level in level_slices:
                count = level.stop - level.start

                if count == 1:
                    y[level.start] = axial[level.start]
                    continue

                offsets = np.linspace(-half_spread, half_spread, count)
                y[level] = axial[level] + offsets

        return radial.copy(), y, normalized_mode

    if normalized_mode == "indexed_levels":
        y = np.empty_like(axial, dtype=float)

        for level_index, level in enumerate(level_slices, start=1):
            count = level.stop - level.start

            if count == 1:
                y[level.start] = float(level_index)
                continue

            offsets = np.linspace(-0.28, 0.28, count)
            y[level] = float(level_index) + offsets

        return radial.copy(), y, normalized_mode

    raise ValueError(
        "display_mode must be 'auto', 'scatter', 'jittered', or 'indexed_levels'."
    )


def plot_quadrature_set(
    quadrature: QuadratureSet,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    display_mode: str = "auto",
    jitter_fraction: float = 0.60,
    show_unit_circle: bool = True,
    show_zero_weight_directions: bool = True,
    scale_markers_by_weight: bool = True,
    annotate_levels: bool = False,
    show_level_guides: bool = True,
    show_legend: bool = True,
    label_every_nth_level: int = 1,
) -> tuple[Figure, Axes]:
    """
    Plot a DORT quadrature set.

    Parameters
    ----------
    quadrature
        Generated quadrature set.
    ax
        Existing Matplotlib axes. If omitted, a new figure is created.
    title
        Optional custom title.
    display_mode
        One of:

        - ``"auto"``
        - ``"scatter"``
        - ``"jittered"``
        - ``"indexed_levels"``

        ``"indexed_levels"`` is often the clearest choice for higher-order
        sets because it separates closely spaced axial-cosine levels.
    jitter_fraction
        For ``display_mode="jittered"``, controls the display-only vertical
        spread of points within each axial level. Must lie between 0 and 1.
    show_unit_circle
        Draw the unit-circle boundary when the display mode uses the physical
        cosine plane.
    show_zero_weight_directions
        Show the zero-weight level-initiating directions.
    scale_markers_by_weight
        Scale marker size by weight.
    annotate_levels
        Annotate the start of each level. For large quadrature sets this is
        best used together with ``label_every_nth_level``.
    show_level_guides
        Draw horizontal guide lines for each level in non-scatter modes.
    show_legend
        Show a legend for integration directions and initiators.
    label_every_nth_level
        When annotating or labeling indexed levels, use every nth level.

    Returns
    -------
    fig, ax
        Matplotlib figure and axes.
    """
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    radial = np.asarray(quadrature.radial_cosine, dtype=float)
    axial = np.asarray(quadrature.axial_cosine, dtype=float)
    weights = np.asarray(quadrature.weights, dtype=float)

    if not (
        radial.ndim == axial.ndim == weights.ndim == 1
        and radial.size == axial.size == weights.size
    ):
        raise ValueError(
            "quadrature arrays must be one-dimensional and of equal length."
        )

    zero_mask = np.isclose(weights, 0.0, atol=1.0e-15)
    nonzero_mask = ~zero_mask

    if scale_markers_by_weight:
        sizes = _marker_sizes_from_weights(weights)
    else:
        sizes = np.full(weights.shape, 36.0, dtype=float)

    display_radial, display_vertical, resolved_mode = _build_display_coordinates(
        quadrature,
        display_mode=display_mode,
        jitter_fraction=jitter_fraction,
    )

    level_slices = _find_level_slices(axial)

    if resolved_mode in {"scatter", "jittered"} and show_unit_circle:
        angle = np.linspace(0.0, 2.0 * np.pi, 361)
        ax.plot(np.cos(angle), np.sin(angle), linewidth=1.0)

    if resolved_mode == "indexed_levels" and show_level_guides:
        for level_index in range(1, len(level_slices) + 1):
            ax.axhline(level_index, linewidth=0.6, alpha=0.25)

    if resolved_mode == "jittered" and show_level_guides:
        for level in level_slices:
            ax.axhline(axial[level.start], linewidth=0.6, alpha=0.25)

    if np.any(nonzero_mask):
        ax.scatter(
            display_radial[nonzero_mask],
            display_vertical[nonzero_mask],
            s=sizes[nonzero_mask],
            alpha=0.75,
            label="Integration directions",
        )

    if show_zero_weight_directions and np.any(zero_mask):
        ax.scatter(
            display_radial[zero_mask],
            display_vertical[zero_mask],
            marker="x",
            s=42.0,
            alpha=0.9,
            label="Zero-weight initiators",
        )

    if annotate_levels:
        for level_number, level in enumerate(level_slices, start=1):
            if (level_number - 1) % max(1, int(label_every_nth_level)) != 0:
                continue

            x = display_radial[level.start]
            y = display_vertical[level.start]

            if resolved_mode == "indexed_levels":
                text = f"{level_number} ({axial[level.start]:.3f})"
            else:
                text = str(level_number)

            ax.annotate(
                text,
                (x, y),
                textcoords="offset points",
                xytext=(4, 4),
            )

    ax.set_xlabel("Radial direction cosine")

    if resolved_mode == "indexed_levels":
        ax.set_ylabel("Axial level index")

        level_count = len(level_slices)
        tick_positions = []
        tick_labels = []

        for level_number, level in enumerate(level_slices, start=1):
            if (level_number - 1) % max(1, int(label_every_nth_level)) == 0:
                tick_positions.append(level_number)
                tick_labels.append(f"{level_number}\n{axial[level.start]:.3f}")

        ax.set_yticks(tick_positions)
        ax.set_yticklabels(tick_labels)
        ax.set_ylim(0.4, level_count + 0.6)
        ax.set_aspect("auto")

    else:
        ax.set_ylabel("Axial direction cosine")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-1.05, 1.05)
        ax.set_ylim(-1.05, 1.05)

    ax.grid(alpha=0.25)

    if title is None:
        mode_name = resolved_mode.replace("_", " ")
        title = (
            f"{quadrature.family.capitalize()} quadrature "
            f"({quadrature.direction_count} directions, {mode_name})"
        )

    ax.set_title(title)

    if show_legend:
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc="best")

    return fig, ax


def save_quadrature_plot(
    quadrature: QuadratureSet,
    filename: str | Path,
    *,
    dpi: int = 200,
    display_mode: str = "auto",
    jitter_fraction: float = 0.60,
    show_unit_circle: bool = True,
    show_zero_weight_directions: bool = True,
    scale_markers_by_weight: bool = True,
    annotate_levels: bool = False,
    show_level_guides: bool = True,
    label_every_nth_level: int = 1,
) -> Path:
    """
    Save a quadrature-direction distribution plot to disk.
    """
    fig, _ = plot_quadrature_set(
        quadrature,
        display_mode=display_mode,
        jitter_fraction=jitter_fraction,
        show_unit_circle=show_unit_circle,
        show_zero_weight_directions=show_zero_weight_directions,
        scale_markers_by_weight=scale_markers_by_weight,
        annotate_levels=annotate_levels,
        show_level_guides=show_level_guides,
        label_every_nth_level=label_every_nth_level,
    )

    path = Path(filename)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return path


def plot_weight_distribution(
    quadrature: QuadratureSet,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    include_zero_weight_directions: bool = False,
) -> tuple[Figure, Axes]:
    """
    Plot directional weights against direction index.

    This is useful for identifying negative or highly irregular weights.
    """
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    weights = np.asarray(quadrature.weights, dtype=float)

    if include_zero_weight_directions:
        indices = np.arange(1, weights.size + 1)
        plotted_weights = weights
    else:
        mask = np.abs(weights) > 1.0e-15
        indices = np.arange(1, int(np.count_nonzero(mask)) + 1)
        plotted_weights = weights[mask]

    ax.plot(indices, plotted_weights, marker="o", linestyle="")

    ax.set_xlabel("Direction index")
    ax.set_ylabel("Weight")
    ax.grid(alpha=0.25)

    if title is None:
        title = f"{quadrature.family.capitalize()} quadrature weights"

    ax.set_title(title)

    return fig, ax


def save_weight_distribution_plot(
    quadrature: QuadratureSet,
    filename: str | Path,
    *,
    dpi: int = 200,
    include_zero_weight_directions: bool = False,
) -> Path:
    """
    Save a directional-weight distribution plot directly to disk.
    """
    fig, _ = plot_weight_distribution(
        quadrature,
        include_zero_weight_directions=include_zero_weight_directions,
    )

    path = Path(filename)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return path


def _quadrant_mask(
    radial_cosine: np.ndarray,
    axial_cosine: np.ndarray,
    quadrant: int,
    *,
    tolerance: float = 1.0e-14,
) -> np.ndarray:
    """
    Return a Boolean mask for one R-Z angular quadrant.

    Quadrant numbering follows the usual Cartesian convention in the
    (radial cosine, axial cosine) plane:

    ``1``
        radial >= 0, axial >= 0

    ``2``
        radial <= 0, axial >= 0

    ``3``
        radial <= 0, axial <= 0

    ``4``
        radial >= 0, axial <= 0

    Directions lying exactly on an axis are included in either adjacent
    quadrant within ``tolerance``.  Such points are uncommon for the standard
    quadrature families used here.
    """
    if quadrant not in (1, 2, 3, 4):
        raise ValueError("quadrant must be one of 1, 2, 3, or 4.")

    radial_positive = radial_cosine >= -tolerance
    radial_negative = radial_cosine <= tolerance
    axial_positive = axial_cosine >= -tolerance
    axial_negative = axial_cosine <= tolerance

    if quadrant == 1:
        return radial_positive & axial_positive
    if quadrant == 2:
        return radial_negative & axial_positive
    if quadrant == 3:
        return radial_negative & axial_negative

    return radial_positive & axial_negative


def _quadrant_surface_coordinates(
    quadrant: int,
    *,
    axial_samples: int = 36,
    azimuth_samples: int = 48,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Construct a smooth unit-sphere surface for one DORT quadrant.

    The returned coordinates are:

    ``x``
        radial direction cosine

    ``y``
        non-negative azimuthal/third direction cosine

    ``z``
        axial direction cosine

    Only one sign of the third cosine is needed because the 2-D DORT
    representation exploits symmetry in that unrepresented direction.
    """
    if quadrant not in (1, 2, 3, 4):
        raise ValueError("quadrant must be one of 1, 2, 3, or 4.")

    axial_magnitude = np.linspace(0.0, 1.0, axial_samples)
    azimuth = np.linspace(0.0, 0.5 * np.pi, azimuth_samples)

    axial_grid, azimuth_grid = np.meshgrid(
        axial_magnitude,
        azimuth,
        indexing="ij",
    )

    transverse_radius = np.sqrt(
        np.clip(1.0 - axial_grid**2, 0.0, None)
    )

    radial_magnitude = transverse_radius * np.cos(azimuth_grid)
    third_cosine = transverse_radius * np.sin(azimuth_grid)

    radial_sign = 1.0 if quadrant in (1, 4) else -1.0
    axial_sign = 1.0 if quadrant in (1, 2) else -1.0

    radial = radial_sign * radial_magnitude
    axial = axial_sign * axial_grid

    return radial, third_cosine, axial


def plot_quadrature_3d(
    quadrature: QuadratureSet,
    *,
    quadrant: int = 1,
    ax=None,
    title: str | None = None,
    show_quadrant_surface: bool = True,
    show_zero_weight_directions: bool = False,
    scale_markers_by_weight: bool = True,
    show_projection_lines: bool = False,
    view_preset: str = "origin_far",
    view_elevation: float | None = None,
    view_azimuth: float | None = None,
    show_legend: bool = True,
):
    """
    Plot quadrature directions in 3-D on one unit-sphere quadrant.

    Parameters
    ----------
    quadrature
        Generated quadrature set.
    quadrant
        R-Z angular quadrant to display:

        - ``1``: radial >= 0, axial >= 0
        - ``2``: radial <= 0, axial >= 0
        - ``3``: radial <= 0, axial <= 0
        - ``4``: radial >= 0, axial <= 0

    ax
        Existing Matplotlib 3-D axes. If omitted, a new 3-D figure is
        created.
    title
        Optional custom title.
    show_quadrant_surface
        Draw a translucent wireframe of the corresponding unit-sphere
        quadrant.
    show_zero_weight_directions
        Include DORT's zero-weight level-initiating directions.
    scale_markers_by_weight
        Scale integration-direction marker area using the directional weight.
    show_projection_lines
        Draw a light line from each integration point down to the
        radial-axial plane (third cosine = 0). This can make the relation
        between the 2-D DORT cosine map and the 3-D sphere easier to see.
    view_preset
        Camera convention. ``"origin_far"`` (default) places the viewer on
        the outside of the selected spherical quadrant and looks inward, so
        the origin is the far/back point. ``"origin_near"`` gives the
        opposite perspective.
    view_elevation
        Optional manual Matplotlib 3-D elevation angle in degrees.
    view_azimuth
        Optional manual Matplotlib 3-D azimuth angle in degrees.
    show_legend
        Show the marker legend.

    Returns
    -------
    fig, ax
        Matplotlib figure and 3-D axes.

    Notes
    -----
    DORT explicitly stores only the radial and axial direction cosines.
    The plotted third coordinate is reconstructed as

    ``sqrt(1 - radial_cosine**2 - axial_cosine**2)``.

    The positive third-cosine branch is shown because the two-dimensional
    formulation represents the opposite azimuthal sign by symmetry.
    """
    radial = np.asarray(quadrature.radial_cosine, dtype=float)
    axial = np.asarray(quadrature.axial_cosine, dtype=float)
    weights = np.asarray(quadrature.weights, dtype=float)

    if not (
        radial.ndim == axial.ndim == weights.ndim == 1
        and radial.size == axial.size == weights.size
    ):
        raise ValueError(
            "quadrature arrays must be one-dimensional and of equal length."
        )

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")
    else:
        fig = ax.figure

        if not hasattr(ax, "zaxis"):
            raise TypeError("ax must be a Matplotlib 3-D axes.")

    mask = _quadrant_mask(radial, axial, quadrant)
    zero_mask = np.isclose(weights, 0.0, atol=1.0e-15)
    integration_mask = mask & ~zero_mask
    initiator_mask = mask & zero_mask

    third_cosine = np.sqrt(
        np.clip(
            1.0 - radial**2 - axial**2,
            0.0,
            None,
        )
    )

    if scale_markers_by_weight:
        marker_sizes = _marker_sizes_from_weights(
            weights,
            minimum_size=18.0,
            maximum_size=120.0,
        )
    else:
        marker_sizes = np.full(weights.shape, 34.0, dtype=float)

    if show_quadrant_surface:
        surface_r, surface_third, surface_z = (
            _quadrant_surface_coordinates(quadrant)
        )

        ax.plot_wireframe(
            surface_r,
            surface_third,
            surface_z,
            rstride=4,
            cstride=5,
            linewidth=0.45,
            alpha=0.22,
        )

    if np.any(integration_mask):
        ax.scatter(
            radial[integration_mask],
            third_cosine[integration_mask],
            axial[integration_mask],
            s=marker_sizes[integration_mask],
            alpha=0.82,
            depthshade=True,
            label="Integration directions",
        )

    if show_zero_weight_directions and np.any(initiator_mask):
        ax.scatter(
            radial[initiator_mask],
            third_cosine[initiator_mask],
            axial[initiator_mask],
            marker="x",
            s=45.0,
            alpha=0.95,
            depthshade=False,
            label="Zero-weight initiators",
        )

    if show_projection_lines and np.any(integration_mask):
        selected_indices = np.flatnonzero(integration_mask)

        for index in selected_indices:
            ax.plot(
                [radial[index], radial[index]],
                [0.0, third_cosine[index]],
                [axial[index], axial[index]],
                linewidth=0.45,
                alpha=0.18,
            )

    ax.set_xlabel("Radial cosine")
    ax.set_ylabel("Third / azimuthal cosine")
    ax.set_zlabel("Axial cosine")

    radial_limits = {
        1: (-0.02, 1.02),
        2: (-1.02, 0.02),
        3: (-1.02, 0.02),
        4: (-0.02, 1.02),
    }
    axial_limits = {
        1: (-0.02, 1.02),
        2: (-0.02, 1.02),
        3: (-1.02, 0.02),
        4: (-1.02, 0.02),
    }

    ax.set_xlim(*radial_limits[quadrant])
    ax.set_ylim(-0.02, 1.02)
    ax.set_zlim(*axial_limits[quadrant])

    # Equal box aspect gives a geometrically meaningful quarter-sphere.
    try:
        ax.set_box_aspect((1.0, 1.0, 1.0))
    except AttributeError:
        pass

    # Camera convention:
    # place the observer on the OUTER side of the selected spherical
    # quadrant and look inward toward (0, 0, 0). This keeps the quadrature
    # directions in front of the origin and makes the origin the farther
    # point of the perspective.
    preset = str(view_preset).strip().lower()

    if preset not in {"origin_far", "origin_near"}:
        raise ValueError(
            "view_preset must be 'origin_far' or 'origin_near'."
        )

    far_azimuth = {
        1: 45.0,
        2: 135.0,
        3: 135.0,
        4: 45.0,
    }[quadrant]

    far_elevation = {
        1: 28.0,
        2: 28.0,
        3: -28.0,
        4: -28.0,
    }[quadrant]

    if preset == "origin_far":
        automatic_azimuth = far_azimuth
        automatic_elevation = far_elevation
    else:
        automatic_azimuth = far_azimuth - 180.0
        automatic_elevation = -far_elevation

    if view_azimuth is None:
        view_azimuth = automatic_azimuth

    if view_elevation is None:
        view_elevation = automatic_elevation

    ax.view_init(
        elev=float(view_elevation),
        azim=float(view_azimuth),
    )

    if title is None:
        title = (
            f"{quadrature.family.capitalize()} quadrature — "
            f"3-D quadrant {quadrant}"
        )

    ax.set_title(title)

    if show_legend:
        handles, labels = ax.get_legend_handles_labels()

        if handles:
            ax.legend(loc="best")

    return fig, ax


def save_quadrature_3d_plot(
    quadrature: QuadratureSet,
    filename: str | Path,
    *,
    quadrant: int = 1,
    dpi: int = 200,
    show_quadrant_surface: bool = True,
    show_zero_weight_directions: bool = False,
    scale_markers_by_weight: bool = True,
    show_projection_lines: bool = False,
    view_preset: str = "origin_far",
    view_elevation: float | None = None,
    view_azimuth: float | None = None,
) -> Path:
    """
    Save the 3-D unit-sphere quadrature plot for one R-Z quadrant.
    """
    fig, _ = plot_quadrature_3d(
        quadrature,
        quadrant=quadrant,
        show_quadrant_surface=show_quadrant_surface,
        show_zero_weight_directions=show_zero_weight_directions,
        scale_markers_by_weight=scale_markers_by_weight,
        show_projection_lines=show_projection_lines,
        view_preset=view_preset,
        view_elevation=view_elevation,
        view_azimuth=view_azimuth,
    )

    path = Path(filename)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return path


if __name__ == "__main__":
    from quadrature import (
        generate_legacy_quadrature,
        generate_product_quadrature,
    )

    legacy = generate_legacy_quadrature(
        order=8,
        symmetry="half",
    )

    save_quadrature_plot(
        legacy,
        "legacy_s8_distribution.png",
        display_mode="scatter",
        annotate_levels=True,
    )

    product = generate_product_quadrature(
        polar_order=24,
        azimuthal_order=32,
    )

    save_quadrature_plot(
        product,
        "product_24x32_distribution.png",
        display_mode="indexed_levels",
        label_every_nth_level=2,
    )

    save_weight_distribution_plot(
        product,
        "product_24x32_weights.png",
    )

    print("Created:")
    print("  legacy_s8_distribution.png")
    print("  product_24x32_distribution.png")
    print("  product_24x32_weights.png")
