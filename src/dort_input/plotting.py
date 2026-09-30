"""Plotting helpers for built DORT R-Z models.

The functions in this module visualize final material filling and region
ownership. They do not alter the model.

R is plotted on the horizontal axis and Z on the vertical axis.
"""

from __future__ import annotations

import csv
from itertools import zip_longest
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib import patheffects

from .model import DORTModel


def _require_built(model: DORTModel) -> None:
    """Require a built model before plotting.
    
    Parameters
    ----------
    model : DORTModel
        Model to check.
    
    Returns
    -------
    None
    
    Raises
    ------
    RuntimeError
        If ``model.build()`` has not been completed successfully.
    """
    if not model.is_built:
        raise RuntimeError(
            "The model must be built before plotting. "
            "Call model.build() first."
        )


def _discrete_index_map(
    values: np.ndarray,
    labels: Iterable[str],
) -> tuple[np.ndarray, dict[str, int]]:
    """Convert categorical labels to integer plotting indices.
    
    Parameters
    ----------
    values : numpy.ndarray
        Array containing string-like category labels.
    labels : iterable of str
        Ordered set of valid category labels.
    
    Returns
    -------
    indexed : numpy.ndarray
        Integer array with the same shape as ``values``.
    label_to_index : dict of str to int
        Mapping from category label to plotting index.
    """
    labels = tuple(labels)
    label_to_index = {
        label: index
        for index, label in enumerate(labels)
    }

    indexed = np.full(values.shape, -1, dtype=int)

    for label, index in label_to_index.items():
        indexed[values == label] = index

    return indexed, label_to_index


def _axis_extent(
    extent: tuple[float, float] | None,
    edges: np.ndarray,
    name: str,
) -> tuple[float, float]:
    """Validate a requested view interval, or use the full mesh interval."""
    if extent is None:
        return float(edges[0]), float(edges[-1])

    try:
        low, high = extent
        low, high = float(low), float(high)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a pair (minimum, maximum).") from exc

    if not np.isfinite(low) or not np.isfinite(high) or low >= high:
        raise ValueError(f"{name} must contain finite, increasing bounds.")
    return low, high


def _visible_labels(
    labels: np.ndarray,
    r_edges: np.ndarray,
    z_edges: np.ndarray,
    r_extent: tuple[float, float],
    z_extent: tuple[float, float],
) -> set[str]:
    """Find categories in cells with non-zero area inside the view."""
    r_visible = (r_edges[:-1] < r_extent[1]) & (r_edges[1:] > r_extent[0])
    z_visible = (z_edges[:-1] < z_extent[1]) & (z_edges[1:] > z_extent[0])
    return set(labels[np.ix_(z_visible, r_visible)].ravel())


def _category_cmap(n_categories: int):
    """Use distinct categorical colors beyond the 20 colors in tab20."""
    if n_categories <= 20:
        return plt.get_cmap("tab20", max(n_categories, 1))

    colors = [
        color
        for palette in ("tab20", "tab20b", "tab20c")
        for color in plt.get_cmap(palette).colors
    ]
    if n_categories > len(colors):
        extra = n_categories - len(colors)
        hsv = plt.get_cmap("hsv", extra)
        colors.extend(hsv(i) for i in range(extra))
    return ListedColormap(colors[:n_categories])


def _add_legend(ax: Axes, handles: list[Patch], title: str, *, color_fill: bool = True) -> None:
    """Keep a long key below the plot instead of obscuring its geometry."""
    if not handles:
        return
    common = dict(
        handles=handles, title=title, fontsize=8, title_fontsize=9,
        frameon=True, fancybox=False, borderpad=0.5,
        labelspacing=0.35, columnspacing=1.2,
        handlelength=1.2 if color_fill else 0,
        handletextpad=0.4 if color_fill else 0,
    )
    if len(handles) <= 8:
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0, **common)
    else:
        columns = min(4, max(2, int(np.ceil(len(handles) / 7))))
        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.13),
            borderaxespad=0, ncol=columns, **common,
        )


def _material_boundary_segments(
    ids: np.ndarray,
    r_edges: np.ndarray,
    z_edges: np.ndarray,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Return mesh-aligned outer edges and interfaces between different IDs.

    Contiguous runs of an interface are merged so fine meshes do not create
    thousands of overlapping line artists.
    """
    segments = [
        ((r_edges[0], z_edges[0]), (r_edges[-1], z_edges[0])),
        ((r_edges[0], z_edges[-1]), (r_edges[-1], z_edges[-1])),
        ((r_edges[0], z_edges[0]), (r_edges[0], z_edges[-1])),
        ((r_edges[-1], z_edges[0]), (r_edges[-1], z_edges[-1])),
    ]

    for i in range(1, ids.shape[1]):
        changed = ids[:, i - 1] != ids[:, i]
        starts = np.flatnonzero(changed & ~np.r_[False, changed[:-1]])
        stops = np.flatnonzero(changed & ~np.r_[changed[1:], False]) + 1
        segments.extend(
            ((r_edges[i], z_edges[start]), (r_edges[i], z_edges[stop]))
            for start, stop in zip(starts, stops)
        )

    for j in range(1, ids.shape[0]):
        changed = ids[j - 1, :] != ids[j, :]
        starts = np.flatnonzero(changed & ~np.r_[False, changed[:-1]])
        stops = np.flatnonzero(changed & ~np.r_[changed[1:], False]) + 1
        segments.extend(
            ((r_edges[start], z_edges[j]), (r_edges[stop], z_edges[j]))
            for start, stop in zip(starts, stops)
        )

    return segments


def _geometry_outlines(model: DORTModel) -> dict[str, list]:
    """Use the final cell assignment for each distinct boundary layer."""
    _require_built(model)
    r_edges, z_edges = model.mesh.r.edges, model.mesh.z.edges
    material_ids = model.material_id_map
    regions = model.region_map
    _, region_codes = np.unique(regions, return_inverse=True)
    region_codes = region_codes.reshape(regions.shape)
    joint_codes = (material_ids.astype(np.int64) * (int(region_codes.max()) + 1)
                   + region_codes)
    return {
        "material": _material_boundary_segments(material_ids, r_edges, z_edges),
        "region": _material_boundary_segments(regions, r_edges, z_edges),
        "union": _material_boundary_segments(joint_codes, r_edges, z_edges),
    }


def write_outline_csv(model: DORTModel, filename: str | Path) -> Path:
    """Export material, region, and union outlines for Origin or Excel.

    The CSV has three XY pairs: ``Material_R,Material_Z``,
    ``Region_R,Region_Z``, and ``Union_R,Union_Z``. Each segment is represented
    by its two endpoints followed by an empty row so an XY line plot leaves a
    gap before the next segment. Select each pair as a separate plot series.
    Interfaces are taken from the *built* cell maps, including overlap
    priorities, and collinear mesh edges are merged into longer segments.
    Coordinates use the same units as the model's R and Z boundaries.

    Parameters
    ----------
    model : DORTModel
        Built R-Z model.
    filename : str or pathlib.Path
        Destination CSV path. The parent directory must exist.

    Returns
    -------
    pathlib.Path
        Path of the written CSV file.
    """
    outlines = _geometry_outlines(model)

    def xy_rows(segments):
        for start, stop in segments:
            yield tuple(format(float(value), ".17g") for value in start)
            yield tuple(format(float(value), ".17g") for value in stop)
            yield ("", "")

    path = Path(filename)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("Material_R", "Material_Z", "Region_R", "Region_Z",
                         "Union_R", "Union_Z"))
        for pair_rows in zip_longest(
            *(xy_rows(outlines[name]) for name in ("material", "region", "union")),
            fillvalue=("", ""),
        ):
            writer.writerow(tuple(value for pair in pair_rows for value in pair))
    return path


def _separate_material_labels(ax: Axes, labels: list[tuple]) -> None:
    """Move crowded IDs within their areas, using a leader line if needed."""
    if len(labels) < 2:
        return

    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    plot_box = ax.get_window_extent(renderer)
    placed = []

    # Small areas are the least flexible, so place their labels first.
    for label, cell_centres, area in sorted(labels, key=lambda item: item[2]):
        anchor = label.get_position()
        anchor_px = ax.transData.transform(anchor)
        pixels = ax.transData.transform(cell_centres)
        distances = np.sum((pixels - anchor_px) ** 2, axis=1)
        nearest = np.argsort(distances)[:256]
        candidates = [anchor, *map(tuple, cell_centres[nearest])]
        chosen = False

        def free_at(position):
            label.set_position(position)
            box = label.get_window_extent(renderer).padded(2)
            inside = (plot_box.x0 <= box.x0 and box.x1 <= plot_box.x1
                      and plot_box.y0 <= box.y0 and box.y1 <= plot_box.y1)
            return box if (inside
                           and not any(box.overlaps(other) for other in placed)) else None

        for point in candidates:
            box = free_at(point)
            if box is not None:
                placed.append(box)
                chosen = True
                break

        if chosen:
            continue

        # Extremely small neighboring areas can lack room for their text.
        # Keep the ID readable nearby and point back to its material area.
        directions = ((0, 1), (0, -1), (1, 0), (-1, 0),
                      (1, 1), (-1, 1), (1, -1), (-1, -1))
        for radius in (18, 30, 45, 65, 90, 125):
            for dx, dy in directions:
                xy = ax.transData.inverted().transform(
                    anchor_px + radius * np.array((dx, dy))
                )
                box = free_at(tuple(xy))
                if box is not None:
                    placed.append(box)
                    ax.annotate(
                        "", xy=anchor, xytext=tuple(xy),
                        arrowprops=dict(arrowstyle="-", color="0.35", lw=0.6),
                        zorder=4,
                    )
                    chosen = True
                    break
            if chosen:
                break

        if not chosen:
            # Keep the label rather than silently dropping a material ID.
            label.set_position(anchor)
            placed.append(label.get_window_extent(renderer).padded(2))


def _label_material_areas(
    ax: Axes,
    ids: np.ndarray,
    r_edges: np.ndarray,
    z_edges: np.ndarray,
    r_extent: tuple[float, float],
    z_extent: tuple[float, float],
    label_text: dict[int, str] | None = None,
) -> None:
    """Place one ID or supplied name in each visible, edge-connected area.

    The centre uses visible R-Z area (including partial cells at the view
    edges). If it falls in a hole or another material, a cell in the same
    area nearest to that centre is chosen instead.
    """
    r_visible = np.flatnonzero(
        (r_edges[:-1] < r_extent[1]) & (r_edges[1:] > r_extent[0])
    )
    z_visible = np.flatnonzero(
        (z_edges[:-1] < z_extent[1]) & (z_edges[1:] > z_extent[0])
    )
    if not r_visible.size or not z_visible.size:
        return

    r_start, r_stop = r_visible[0], r_visible[-1] + 1
    z_start, z_stop = z_visible[0], z_visible[-1] + 1
    visible_ids = ids[z_start:z_stop, r_start:r_stop]
    r_left = np.maximum(r_edges[r_start:r_stop], r_extent[0])
    r_right = np.minimum(r_edges[r_start + 1:r_stop + 1], r_extent[1])
    z_bottom = np.maximum(z_edges[z_start:z_stop], z_extent[0])
    z_top = np.minimum(z_edges[z_start + 1:z_stop + 1], z_extent[1])
    r_centres = (r_left + r_right) / 2
    z_centres = (z_bottom + z_top) / 2
    visited = np.zeros(visible_ids.shape, dtype=bool)
    height, width = visible_ids.shape
    labels = []

    for row in range(height):
        for col in range(width):
            if visited[row, col]:
                continue

            material_id = visible_ids[row, col]
            visited[row, col] = True
            stack = [(row, col)]
            cells = []
            while stack:
                j, i = stack.pop()
                cells.append((j, i))
                for neighbour_j, neighbour_i in (
                    (j - 1, i), (j + 1, i), (j, i - 1), (j, i + 1)
                ):
                    if (0 <= neighbour_j < height and 0 <= neighbour_i < width
                            and not visited[neighbour_j, neighbour_i]
                            and visible_ids[neighbour_j, neighbour_i] == material_id):
                        visited[neighbour_j, neighbour_i] = True
                        stack.append((neighbour_j, neighbour_i))

            rows, cols = np.asarray(cells, dtype=int).T
            weights = (r_right[cols] - r_left[cols]) * (z_top[rows] - z_bottom[rows])
            r_centre = float(np.average(r_centres[cols], weights=weights))
            z_centre = float(np.average(z_centres[rows], weights=weights))

            # A centroid may lie outside a concave material area or in a hole.
            i = int(np.searchsorted(r_edges, r_centre, side="right") - 1 - r_start)
            j = int(np.searchsorted(z_edges, z_centre, side="right") - 1 - z_start)
            if not (0 <= i < width and 0 <= j < height
                    and visible_ids[j, i] == material_id
                    and visited[j, i]
                    and np.any((rows == j) & (cols == i))):
                nearest = np.argmin(
                    (r_centres[cols] - r_centre) ** 2
                    + (z_centres[rows] - z_centre) ** 2
                )
                r_centre = float(r_centres[cols[nearest]])
                z_centre = float(z_centres[rows[nearest]])

            text = (str(material_id) if label_text is None
                    else label_text[int(material_id)])
            label = ax.text(
                r_centre, z_centre, text, ha="center", va="center",
                fontsize=9, fontweight="bold", clip_on=True, zorder=5,
            )
            label.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground="white")])
            if label_text is not None:
                # Multiword material names can be wider than a thin region.
                # Measure the actual rendered text in the visible area before
                # resorting to a leader label outside that area.
                renderer = ax.figure.canvas.get_renderer()
                left = ax.transData.transform((min(r_left[cols]), z_centre))[0]
                right = ax.transData.transform((max(r_right[cols]), z_centre))[0]
                available_width = abs(right - left) - 6
                if label.get_window_extent(renderer).width > available_width:
                    words = text.split()
                    if len(words) > 1:
                        label.set_text("\n".join(words))
                    while (label.get_window_extent(renderer).width > available_width
                           and label.get_fontsize() > 6):
                        label.set_fontsize(label.get_fontsize() - 0.5)
            cell_centres = np.column_stack((r_centres[cols], z_centres[rows]))
            labels.append((label, cell_centres, float(np.sum(weights))))

    _separate_material_labels(ax, labels)


def plot_materials(
    model: DORTModel,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    show_mesh: bool = False,
    show_ids: bool = False,
    show_material_boundaries: bool = False,
    show_material_ids: bool = False,
    color_fill: bool = True,
    aspect: str | float | None = None,
    figsize: tuple[float, float] | None = None,
    r_extent: tuple[float, float] | None = None,
    z_extent: tuple[float, float] | None = None,
    legend: bool = True,
) -> tuple[Figure, Axes]:
    """Plot final material filling in R-Z coordinates.
    
    Parameters
    ----------
    model : DORTModel
        Built model.
    ax : matplotlib.axes.Axes, optional
        Existing axes. A new figure/axes pair is created when omitted.
    title : str, optional
        Plot title. Defaults to ``"<model name> - material map"``.
    show_mesh : bool, optional
        Draw fine-mesh cell boundaries.
    show_ids : bool, optional
        Annotate cells with internal material IDs. Intended for small meshes.
    show_material_boundaries : bool, optional
        Draw lines at the outer model edges and at interfaces where the final
        material ID changes. Unlike ``show_mesh``, this omits internal cell edges.
    show_material_ids : bool, optional
        Put one material ID near the centre of each connected visible material
        area. Disconnected areas of the same material are labeled separately.
    color_fill : bool, optional
        If ``False``, draw an unfilled map with material boundaries and one ID
        per visible material area. These two options are enabled automatically.
    aspect : {"auto", "equal"} or float, optional
        Plot aspect. Defaults to ``"auto"`` when IDs are shown, giving narrow
        regions more horizontal space; otherwise defaults to ``"equal"``.
        Set ``"equal"`` to preserve physical R-Z proportions.
    figsize : tuple of float, optional
        Figure width and height in inches when a new axes is created. ID plots
        use a wider figure by default. Ignored when ``ax`` is supplied.
    r_extent, z_extent : tuple of float, optional
        Visible ``(minimum, maximum)`` in R and Z. Omitted axes show the full
        mesh. The view can cut through mesh cells; labels use visible areas.
    legend : bool, optional
        Display the material legend.
    
    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure containing the plot.
    ax : matplotlib.axes.Axes
        Axes containing the plot.
    
    Raises
    ------
    RuntimeError
        If the model has not been built.
    ValueError
        If a final material label cannot be mapped to a plotted category.
    """
    _require_built(model)

    r_edges = model.mesh.r.edges
    z_edges = model.mesh.z.edges
    r_limits = _axis_extent(r_extent, r_edges, "r_extent")
    z_limits = _axis_extent(z_extent, z_edges, "z_extent")
    show_material_boundaries = show_material_boundaries or not color_fill
    show_material_ids = show_material_ids or not color_fill

    material_names = model.material_name_map

    # Preserve material registry order, but only plot materials actually used.
    used_materials = [
        material.name
        for material in model.materials
        if np.any(material_names == material.name)
    ]

    if np.any(material_names == ""):
        used_materials.append("<unfilled>")

    plot_names = material_names.copy()
    plot_names[plot_names == ""] = "<unfilled>"

    indexed, label_to_index = _discrete_index_map(
        plot_names,
        used_materials,
    )

    if np.any(indexed < 0):
        unknown = np.unique(plot_names[indexed < 0])
        raise ValueError(
            "Material plot contains labels that were not mapped: "
            f"{unknown.tolist()}"
        )

    n_categories = len(used_materials)
    cmap = _category_cmap(n_categories)
    visible_names = _visible_labels(plot_names, r_edges, z_edges, r_limits, z_limits)

    if ax is None:
        default_size = (12, 7.5) if (show_ids or show_material_ids or n_categories > 8) else (8, 5.5)
        fig, ax = plt.subplots(figsize=figsize or default_size, layout="constrained")
    else:
        fig = ax.figure

    edgecolors = "face"
    linewidth = 0.0

    if show_mesh:
        edgecolors = "k"
        linewidth = 0.25

    if color_fill:
        ax.pcolormesh(
            r_edges, z_edges, indexed, cmap=cmap, shading="flat",
            edgecolors=edgecolors, linewidth=linewidth,
            vmin=-0.5, vmax=max(n_categories - 0.5, 0.5),
        )
    elif show_mesh:
        ax.vlines(r_edges, z_edges[0], z_edges[-1], color="0.86", linewidth=0.3)
        ax.hlines(z_edges, r_edges[0], r_edges[-1], color="0.86", linewidth=0.3)

    material_ids = None
    if show_material_boundaries or show_material_ids or show_ids:
        material_ids = model.material_id_map
    if show_material_boundaries:
        ax.add_collection(LineCollection(
            _material_boundary_segments(material_ids, r_edges, z_edges),
            colors="black", linewidths=0.9, zorder=3,
        ))

    ax.set_xlabel("R")
    ax.set_ylabel("Z")
    ax.set_aspect(
        aspect if aspect is not None else ("auto" if (show_ids or show_material_ids) else "equal"),
        adjustable="box",
    )
    ax.set_xlim(r_limits)
    ax.set_ylim(z_limits)

    if title is None:
        title = f"{model.name} - material map"

    ax.set_title(title)

    if legend and visible_names:
        handles = []
        name_to_id = {material.name: material.material_id for material in model.materials}

        for label, index in label_to_index.items():
            if label not in visible_names:
                continue
            material_id = name_to_id.get(label, 0)
            legend_label = f"{material_id}: {label}" if (show_ids or show_material_ids) else label
            handles.append(
                Patch(
                    facecolor=cmap(index) if color_fill else "none",
                    edgecolor="none",
                    label=legend_label,
                )
            )

        _add_legend(
            ax, handles,
            "Material ID — Name" if (show_ids or show_material_ids) else "Materials",
            color_fill=color_fill,
        )

    if show_ids:
        r_centers = model.mesh.r.centers
        z_centers = model.mesh.z.centers

        for j, zc in enumerate(z_centers):
            if not z_limits[0] <= zc <= z_limits[1]:
                continue
            for i, rc in enumerate(r_centers):
                if not r_limits[0] <= rc <= r_limits[1]:
                    continue
                ax.text(
                    rc,
                    zc,
                    str(material_ids[j, i]),
                    ha="center",
                    va="center",
                    fontsize=7,
                    clip_on=True,
                )

    if show_material_ids:
        _label_material_areas(ax, material_ids, r_edges, z_edges, r_limits, z_limits)

    return fig, ax


def plot_regions(
    model: DORTModel,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    show_mesh: bool = False,
    aspect: str | float = "equal",
    figsize: tuple[float, float] | None = None,
    r_extent: tuple[float, float] | None = None,
    z_extent: tuple[float, float] | None = None,
    legend: bool = True,
) -> tuple[Figure, Axes]:
    """Plot final region ownership in R-Z coordinates.
    
    Parameters
    ----------
    model : DORTModel
        Built model.
    ax : matplotlib.axes.Axes, optional
        Existing axes. A new figure/axes pair is created when omitted.
    title : str, optional
        Plot title. Defaults to ``"<model name> - region map"``.
    show_mesh : bool, optional
        Draw fine-mesh cell boundaries.
    aspect : {"auto", "equal"} or float, optional
        Plot aspect. The default preserves physical R-Z proportions.
    figsize : tuple of float, optional
        Figure width and height in inches when a new axes is created.
    r_extent, z_extent : tuple of float, optional
        Visible ``(minimum, maximum)`` in R and Z. Omitted axes show the full
        mesh; the view can cut through cells.
    legend : bool, optional
        Display the region legend.
    
    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure containing the plot.
    ax : matplotlib.axes.Axes
        Axes containing the plot.
    
    Raises
    ------
    RuntimeError
        If the model has not been built.
    ValueError
        If a final owner label cannot be mapped to a plotted category.
    
    Notes
    -----
    This plot preserves geometric-region identity even when two distinct regions
    use the same physical material.
    """
    _require_built(model)

    r_edges = model.mesh.r.edges
    z_edges = model.mesh.z.edges
    r_limits = _axis_extent(r_extent, r_edges, "r_extent")
    z_limits = _axis_extent(z_extent, z_edges, "z_extent")

    region_names = model.region_map

    ordered_regions: list[str] = []

    if np.any(region_names == "background"):
        ordered_regions.append("background")

    for region in model.regions:
        if region.enabled and np.any(region_names == region.name):
            ordered_regions.append(region.name)

    if np.any(region_names == ""):
        ordered_regions.append("<unfilled>")

    plot_names = region_names.copy()
    plot_names[plot_names == ""] = "<unfilled>"

    indexed, label_to_index = _discrete_index_map(
        plot_names,
        ordered_regions,
    )

    if np.any(indexed < 0):
        unknown = np.unique(plot_names[indexed < 0])
        raise ValueError(
            "Region plot contains labels that were not mapped: "
            f"{unknown.tolist()}"
        )

    n_categories = len(ordered_regions)
    cmap = _category_cmap(n_categories)
    visible_names = _visible_labels(plot_names, r_edges, z_edges, r_limits, z_limits)

    if ax is None:
        default_size = (12, 7.5) if n_categories > 8 else (8, 5.5)
        fig, ax = plt.subplots(figsize=figsize or default_size, layout="constrained")
    else:
        fig = ax.figure

    edgecolors = "face"
    linewidth = 0.0

    if show_mesh:
        edgecolors = "k"
        linewidth = 0.25

    ax.pcolormesh(
        r_edges,
        z_edges,
        indexed,
        cmap=cmap,
        shading="flat",
        edgecolors=edgecolors,
        linewidth=linewidth,
        vmin=-0.5,
        vmax=max(n_categories - 0.5, 0.5),
    )

    ax.set_xlabel("R")
    ax.set_ylabel("Z")
    ax.set_aspect(aspect, adjustable="box")
    ax.set_xlim(r_limits)
    ax.set_ylim(z_limits)

    if title is None:
        title = f"{model.name} - region map"

    ax.set_title(title)

    if legend and visible_names:
        handles = []

        for label, index in label_to_index.items():
            if label not in visible_names:
                continue
            handles.append(
                Patch(
                    facecolor=cmap(index),
                    label=label,
                )
            )

        _add_legend(ax, handles, "Regions")

    return fig, ax


def plot_material_region_union(
    model: DORTModel,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    show_mesh: bool = False,
    show_material_labels: bool = True,
    aspect: str | float = "auto",
    figsize: tuple[float, float] | None = None,
    r_extent: tuple[float, float] | None = None,
    z_extent: tuple[float, float] | None = None,
    legend: bool = True,
) -> tuple[Figure, Axes]:
    """Fill by material, encase every final region, and label its material.

    An outline is drawn wherever either the material ID or the region owner
    changes. Adjacent regions with the same material retain their separating
    boundary and each connected area receives its material name. Outer model
    edges are included. Labels use the visible part of each connected area
    when an R-Z extent is supplied.
    """
    _require_built(model)
    title = title if title is not None else f"{model.name} - material and region outlines"
    fig, ax = plot_materials(
        model, ax=ax, title=title, show_mesh=show_mesh,
        show_material_boundaries=False, show_material_ids=False,
        aspect=aspect, figsize=figsize, r_extent=r_extent,
        z_extent=z_extent, legend=legend,
    )
    r_edges, z_edges = model.mesh.r.edges, model.mesh.z.edges
    material_ids = model.material_id_map
    material_names = model.material_name_map
    regions = model.region_map
    _, codes = np.unique(regions, return_inverse=True)
    codes = codes.reshape(regions.shape)
    joint_codes = (material_ids.astype(np.int64) * (int(codes.max()) + 1) + codes)
    ax.add_collection(LineCollection(
        _geometry_outlines(model)["union"],
        colors="black", linewidths=0.9, zorder=3,
    ))
    if show_material_labels:
        names = {}
        for code, name in zip(joint_codes.flat, material_names.flat):
            names.setdefault(int(code), str(name) if name else "<unfilled>")
        _label_material_areas(ax, joint_codes, r_edges, z_edges,
                              _axis_extent(r_extent, r_edges, "r_extent"),
                              _axis_extent(z_extent, z_edges, "z_extent"),
                              label_text=names)
    return fig, ax


def save_material_region_union_plot(
    model: DORTModel, filename: str | Path, *, dpi: int = 200, **kwargs
) -> None:
    """Save :func:`plot_material_region_union` to an image file."""
    fig, _ = plot_material_region_union(model, **kwargs)
    try:
        fig.savefig(filename, dpi=dpi, bbox_inches="tight")
    finally:
        plt.close(fig)


def save_material_plot(
    model: DORTModel,
    filename: str,
    *,
    dpi: int = 200,
    show_mesh: bool = False,
    show_ids: bool = False,
    show_material_boundaries: bool = False,
    show_material_ids: bool = False,
    color_fill: bool = True,
    aspect: str | float | None = None,
    figsize: tuple[float, float] | None = None,
    r_extent: tuple[float, float] | None = None,
    z_extent: tuple[float, float] | None = None,
    legend: bool = True,
) -> None:
    """Create and save a material-map plot.
    
    Parameters
    ----------
    model : DORTModel
        Built model.
    filename : str or path-like
        Output image path accepted by Matplotlib.
    dpi : int, optional
        Output resolution in dots per inch.
    show_mesh : bool, optional
        Draw fine-mesh boundaries.
    show_ids : bool, optional
        Annotate cells with internal material IDs.
    show_material_boundaries : bool, optional
        Draw lines at changes in the final material ID and at the model edge.
    show_material_ids : bool, optional
        Label each visible connected material area once.
    color_fill : bool, optional
        If ``False``, draw only material boundaries and IDs on a white plot.
    aspect : {"auto", "equal"} or float, optional
        Plot aspect. Defaults to ``"auto"`` if IDs are shown.
    figsize : tuple of float, optional
        New figure width and height in inches.
    r_extent, z_extent : tuple of float, optional
        Visible ``(minimum, maximum)`` in R and Z.
    legend : bool, optional
        Show the key with ID–name pairs when IDs are displayed.
    
    Returns
    -------
    None
    """
    fig, _ = plot_materials(
        model,
        show_mesh=show_mesh,
        show_ids=show_ids,
        show_material_boundaries=show_material_boundaries,
        show_material_ids=show_material_ids,
        color_fill=color_fill,
        aspect=aspect,
        figsize=figsize,
        r_extent=r_extent,
        z_extent=z_extent,
        legend=legend,
    )

    fig.savefig(
        filename,
        dpi=dpi,
        bbox_inches="tight",
    )

    plt.close(fig)


def save_region_plot(
    model: DORTModel,
    filename: str,
    *,
    dpi: int = 200,
    show_mesh: bool = False,
    aspect: str | float = "equal",
    figsize: tuple[float, float] | None = None,
    r_extent: tuple[float, float] | None = None,
    z_extent: tuple[float, float] | None = None,
    legend: bool = True,
) -> None:
    """Create and save a region-ownership plot.
    
    Parameters
    ----------
    model : DORTModel
        Built model.
    filename : str or path-like
        Output image path accepted by Matplotlib.
    dpi : int, optional
        Output resolution in dots per inch.
    show_mesh : bool, optional
        Draw fine-mesh boundaries.
    aspect : {"auto", "equal"} or float, optional
        Plot aspect.
    figsize : tuple of float, optional
        New figure width and height in inches.
    r_extent, z_extent : tuple of float, optional
        Visible ``(minimum, maximum)`` in R and Z.
    legend : bool, optional
        Display the region key.
    
    Returns
    -------
    None
    """
    fig, _ = plot_regions(
        model,
        show_mesh=show_mesh,
        aspect=aspect,
        figsize=figsize,
        r_extent=r_extent,
        z_extent=z_extent,
        legend=legend,
    )

    fig.savefig(
        filename,
        dpi=dpi,
        bbox_inches="tight",
    )

    plt.close(fig)


if __name__ == "__main__":
    # --------------------------------------------------------------
    # Demonstration / smoke test
    # --------------------------------------------------------------
    from .model import DORTModel

    model = DORTModel("plot_demo")

    model.add_material("Sodium")
    model.add_material("Core")
    model.add_material("SS316")
    model.add_material("Air")

    model.mesh.r.add_segment(
        0.0,
        200.0,
        step=10.0,
    )

    model.mesh.z.add_segment(
        -100.0,
        100.0,
        step=10.0,
    )

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
        "penetration",
        material="Air",
        r=(80.0, 120.0),
        z=(-10.0, 10.0),
        priority=50,
    )

    model.build()

    save_material_plot(
        model,
        "material_map_demo.png",
        show_mesh=True,
    )

    save_region_plot(
        model,
        "region_map_demo.png",
        show_mesh=True,
    )

    print("Created:")
    print("  material_map_demo.png")
    print("  region_map_demo.png")
