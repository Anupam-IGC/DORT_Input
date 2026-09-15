"""
mesh.py
=======

Mesh utilities for a simple Python API used to prepare DORT R-Z models.

This module deliberately knows nothing about materials, regions, or DORT input
syntax. Its only responsibility is to create and validate one-dimensional
mesh axes and combine them into an R-Z mesh.

Example
-------
from mesh import Mesh

mesh = Mesh()

mesh.r.add_segment(0.0, 100.0, step=10.0)
mesh.r.add_segment(100.0, 140.0, step=5.0)
mesh.r.add_segment(140.0, 300.0, step=20.0)

mesh.z.add_segment(-100.0, -50.0, step=10.0)
mesh.z.add_segment(-50.0, 50.0, step=5.0)
mesh.z.add_segment(50.0, 150.0, step=10.0)

print(mesh)
print(mesh.r.edges)
print(mesh.r.centers)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np


def _as_1d_float_array(values: Iterable[float]) -> np.ndarray:
    """Convert values to a finite one-dimensional float array."""
    array = np.asarray(list(values), dtype=float)

    if array.ndim != 1:
        raise ValueError("Mesh edges must be one-dimensional.")

    if array.size < 2:
        raise ValueError("At least two mesh edges are required.")

    if not np.all(np.isfinite(array)):
        raise ValueError("Mesh edges must contain only finite numbers.")

    return array


@dataclass
class MeshAxis:
    """
    One-dimensional mesh axis.

    Parameters
    ----------
    name
        Human-readable name such as ``"R"`` or ``"Z"``.

    Notes
    -----
    Segments are appended sequentially. Once an axis contains mesh edges,
    the start of the next segment must coincide with the current last edge.
    This prevents accidental gaps or overlaps in the mesh definition.
    """

    name: str
    _edges: np.ndarray = field(
        default_factory=lambda: np.array([], dtype=float),
        init=False,
        repr=False,
    )

    # Relative/absolute tolerance used when comparing floating-point edges.
    _rtol: float = field(default=1.0e-10, init=False, repr=False)
    _atol: float = field(default=1.0e-12, init=False, repr=False)

    @property
    def edges(self) -> np.ndarray:
        """Return a copy of the mesh-edge coordinates."""
        return self._edges.copy()

    @property
    def centers(self) -> np.ndarray:
        """Return mesh-cell centre coordinates."""
        if self._edges.size < 2:
            return np.array([], dtype=float)

        return 0.5 * (self._edges[:-1] + self._edges[1:])

    @property
    def widths(self) -> np.ndarray:
        """Return mesh-cell widths."""
        if self._edges.size < 2:
            return np.array([], dtype=float)

        return np.diff(self._edges)

    @property
    def n_cells(self) -> int:
        """Number of mesh cells."""
        return max(self._edges.size - 1, 0)

    @property
    def bounds(self) -> tuple[float, float] | None:
        """Return ``(minimum, maximum)`` axis bounds, or ``None`` if empty."""
        if self._edges.size == 0:
            return None

        return float(self._edges[0]), float(self._edges[-1])

    @property
    def is_defined(self) -> bool:
        """Whether this axis contains at least one mesh cell."""
        return self.n_cells > 0

    def clear(self) -> None:
        """Remove all mesh edges from the axis."""
        self._edges = np.array([], dtype=float)

    def add_segment(
        self,
        start: float,
        end: float,
        *,
        step: float | None = None,
        n_cells: int | None = None,
    ) -> "MeshAxis":
        """
        Append a uniformly spaced mesh segment.

        Specify exactly one of ``step`` or ``n_cells``.

        Examples
        --------
        ``axis.add_segment(0, 100, step=5)``

        ``axis.add_segment(100, 150, n_cells=20)``

        The requested ``step`` must divide the interval within numerical
        tolerance. This avoids silently creating an unexpected short final
        cell.
        """
        start = float(start)
        end = float(end)

        if not np.isfinite(start) or not np.isfinite(end):
            raise ValueError(f"{self.name}: segment bounds must be finite.")

        if end <= start:
            raise ValueError(
                f"{self.name}: segment end ({end}) must be greater "
                f"than start ({start})."
            )

        if (step is None) == (n_cells is None):
            raise ValueError(
                f"{self.name}: specify exactly one of 'step' or 'n_cells'."
            )

        if self._edges.size:
            if not np.isclose(
                start,
                self._edges[-1],
                rtol=self._rtol,
                atol=self._atol,
            ):
                raise ValueError(
                    f"{self.name}: new segment starts at {start}, but the "
                    f"current axis ends at {self._edges[-1]}. Segments must "
                    "be continuous."
                )

            # Replace a numerically equivalent start by the exact stored edge.
            start = float(self._edges[-1])

        if step is not None:
            step = float(step)

            if not np.isfinite(step) or step <= 0.0:
                raise ValueError(f"{self.name}: step must be a positive number.")

            exact_cells = (end - start) / step
            rounded_cells = int(round(exact_cells))

            if rounded_cells < 1 or not np.isclose(
                exact_cells,
                rounded_cells,
                rtol=self._rtol,
                atol=self._atol,
            ):
                raise ValueError(
                    f"{self.name}: step={step} does not divide the interval "
                    f"[{start}, {end}] exactly. Use a compatible step or "
                    "specify n_cells instead."
                )

            n_cells = rounded_cells

        else:
            if isinstance(n_cells, bool) or int(n_cells) != n_cells:
                raise ValueError(f"{self.name}: n_cells must be an integer.")

            n_cells = int(n_cells)

            if n_cells < 1:
                raise ValueError(f"{self.name}: n_cells must be at least 1.")

        new_edges = np.linspace(start, end, n_cells + 1, dtype=float)

        if self._edges.size == 0:
            self._edges = new_edges
        else:
            # Skip the first point because it duplicates the current last edge.
            self._edges = np.concatenate((self._edges, new_edges[1:]))

        self.validate()
        return self

    def add_edges(self, values: Iterable[float]) -> "MeshAxis":
        """
        Append explicitly supplied mesh edges.

        If the axis already exists, the first supplied edge must equal the
        current final edge. The common edge is not duplicated.
        """
        new_edges = _as_1d_float_array(values)

        if not np.all(np.diff(new_edges) > 0.0):
            raise ValueError(
                f"{self.name}: explicit mesh edges must be strictly increasing."
            )

        if self._edges.size == 0:
            self._edges = new_edges
        else:
            if not np.isclose(
                new_edges[0],
                self._edges[-1],
                rtol=self._rtol,
                atol=self._atol,
            ):
                raise ValueError(
                    f"{self.name}: explicit edges begin at {new_edges[0]}, "
                    f"but the current axis ends at {self._edges[-1]}."
                )

            self._edges = np.concatenate((self._edges, new_edges[1:]))

        self.validate()
        return self

    def validate(self) -> None:
        """Raise ``ValueError`` if the axis definition is invalid."""
        if self._edges.size == 0:
            return

        if self._edges.ndim != 1:
            raise ValueError(f"{self.name}: mesh edges must be one-dimensional.")

        if not np.all(np.isfinite(self._edges)):
            raise ValueError(f"{self.name}: mesh edges contain non-finite values.")

        if self._edges.size < 2:
            raise ValueError(f"{self.name}: at least two mesh edges are required.")

        widths = np.diff(self._edges)

        if not np.all(widths > 0.0):
            raise ValueError(
                f"{self.name}: mesh edges must be strictly increasing."
            )

    def __len__(self) -> int:
        return self.n_cells

    def __repr__(self) -> str:
        if not self.is_defined:
            return f"MeshAxis(name={self.name!r}, empty=True)"

        lo, hi = self.bounds
        return (
            f"MeshAxis(name={self.name!r}, n_cells={self.n_cells}, "
            f"bounds=({lo:g}, {hi:g}))"
        )


@dataclass
class Mesh:
    """Two-dimensional cylindrical R-Z mesh."""

    r: MeshAxis = field(default_factory=lambda: MeshAxis("R"))
    z: MeshAxis = field(default_factory=lambda: MeshAxis("Z"))

    @property
    def shape(self) -> tuple[int, int]:
        """
        Return the material-map shape ``(nz, nr)``.

        This convention is used throughout the planned API:
        axis 0 -> Z
        axis 1 -> R
        """
        return self.z.n_cells, self.r.n_cells

    @property
    def n_cells(self) -> int:
        """Total number of R-Z mesh cells."""
        return self.r.n_cells * self.z.n_cells

    def validate(self) -> None:
        """Validate both R and Z axes."""
        self.r.validate()
        self.z.validate()

        if not self.r.is_defined:
            raise ValueError("R mesh has not been defined.")

        if not self.z.is_defined:
            raise ValueError("Z mesh has not been defined.")

    def __repr__(self) -> str:
        return (
            "Mesh("
            f"nr={self.r.n_cells}, "
            f"nz={self.z.n_cells}, "
            f"shape={self.shape}"
            ")"
        )


if __name__ == "__main__":
    # Small demonstration / smoke test.
    mesh = Mesh()

    mesh.r.add_segment(0.0, 100.0, step=10.0)
    mesh.r.add_segment(100.0, 140.0, step=5.0)
    mesh.r.add_segment(140.0, 300.0, step=20.0)

    mesh.z.add_segment(-100.0, -50.0, step=10.0)
    mesh.z.add_segment(-50.0, 50.0, step=5.0)
    mesh.z.add_segment(50.0, 150.0, step=10.0)

    mesh.validate()

    print(mesh)
    print()
    print("R edges   :", mesh.r.edges)
    print("R centers :", mesh.r.centers)
    print("R widths  :", mesh.r.widths)
    print()
    print("Z edges   :", mesh.z.edges)
    print("Z centers :", mesh.z.centers)
    print("Z widths  :", mesh.z.widths)
    print()
    print("Map shape :", mesh.shape)
    print("Cell count:", mesh.n_cells)
