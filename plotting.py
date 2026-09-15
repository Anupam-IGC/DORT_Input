"""
plotting.py
===========

Plotting helpers for the DORT preparation API.

This module visualizes already-built DORTModel objects. It deliberately does
not modify geometry, materials, or region assignments.

Two main plots are provided:

    plot_materials(model)
        Shows the final material filling.

    plot_regions(model)
        Shows the final region ownership after priority overwriting.

The array convention is always:

    shape = (nz, nr)

with R on the horizontal axis and Z on the vertical axis.
"""

from __future__ import annotations

from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from model import DORTModel


def _require_built(model: DORTModel) -> None:
    """Raise if the model has not yet been built."""
    if not model.is_built:
        raise RuntimeError(
            "The model must be built before plotting. "
            "Call model.build() first."
        )


def _discrete_index_map(
    values: np.ndarray,
    labels: Iterable[str],
) -> tuple[np.ndarray, dict[str, int]]:
    """
    Convert an object/string array to integer category indices.

    Parameters
    ----------
    values
        Array of string-like labels.
    labels
        Ordered category labels.

    Returns
    -------
    indexed
        Integer array with the same shape as ``values``.
    label_to_index
        Mapping from label to integer category index.
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


def plot_materials(
    model: DORTModel,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    show_mesh: bool = False,
    show_ids: bool = False,
    legend: bool = True,
) -> tuple[Figure, Axes]:
    """
    Plot the final material filling in R-Z coordinates.

    Parameters
    ----------
    model
        Built DORTModel.
    ax
        Existing Matplotlib axes. If omitted, a new figure is created.
    title
        Optional plot title. Defaults to ``"<model name> - material map"``.
    show_mesh
        If True, draw mesh-cell boundaries.
    show_ids
        If True, annotate each mesh cell with its DORT material ID.
        Best used only for small meshes.
    legend
        If True, show a material legend.

    Returns
    -------
    fig, ax
        Matplotlib figure and axes.
    """
    _require_built(model)

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    r_edges = model.mesh.r.edges
    z_edges = model.mesh.z.edges

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

    # Let Matplotlib choose colors automatically.
    cmap = plt.get_cmap("tab20", max(n_categories, 1))

    edgecolors = "face"
    linewidth = 0.0

    if show_mesh:
        edgecolors = "k"
        linewidth = 0.25

    mesh_plot = ax.pcolormesh(
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
    ax.set_aspect("equal", adjustable="box")

    if title is None:
        title = f"{model.name} - material map"

    ax.set_title(title)

    if legend and used_materials:
        handles = []

        for label, index in label_to_index.items():
            handles.append(
                Patch(
                    facecolor=cmap(index),
                    label=label,
                )
            )

        ax.legend(
            handles=handles,
            title="Materials",
            loc="best",
        )

    if show_ids:
        material_ids = model.material_id_map
        r_centers = model.mesh.r.centers
        z_centers = model.mesh.z.centers

        for j, zc in enumerate(z_centers):
            for i, rc in enumerate(r_centers):
                ax.text(
                    rc,
                    zc,
                    str(material_ids[j, i]),
                    ha="center",
                    va="center",
                    fontsize=7,
                )

    return fig, ax


def plot_regions(
    model: DORTModel,
    *,
    ax: Axes | None = None,
    title: str | None = None,
    show_mesh: bool = False,
    legend: bool = True,
) -> tuple[Figure, Axes]:
    """
    Plot final region ownership in R-Z coordinates.

    This differs from ``plot_materials`` because two different geometric
    regions may contain the same physical material.
    """
    _require_built(model)

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    r_edges = model.mesh.r.edges
    z_edges = model.mesh.z.edges

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
    cmap = plt.get_cmap("tab20", max(n_categories, 1))

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
    ax.set_aspect("equal", adjustable="box")

    if title is None:
        title = f"{model.name} - region map"

    ax.set_title(title)

    if legend and ordered_regions:
        handles = []

        for label, index in label_to_index.items():
            handles.append(
                Patch(
                    facecolor=cmap(index),
                    label=label,
                )
            )

        ax.legend(
            handles=handles,
            title="Regions",
            loc="best",
        )

    return fig, ax


def save_material_plot(
    model: DORTModel,
    filename: str,
    *,
    dpi: int = 200,
    show_mesh: bool = False,
    show_ids: bool = False,
) -> None:
    """
    Save a material-map plot directly to disk.
    """
    fig, _ = plot_materials(
        model,
        show_mesh=show_mesh,
        show_ids=show_ids,
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
) -> None:
    """
    Save a region-map plot directly to disk.
    """
    fig, _ = plot_regions(
        model,
        show_mesh=show_mesh,
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
    from model import DORTModel

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
